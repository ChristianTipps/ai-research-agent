from __future__ import annotations

import asyncio
from typing import Annotated

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .memory import (
    bootstrap_memory,
    list_evaluation_cases,
    load_memory_overview,
    run_quality_evaluations,
    save_evaluation_results,
    sync_approved_update_to_spaces,
)
from .schemas import (
    ActionResponse,
    EvalRunCreate,
    EvalsOverview,
    FeedbackCreate,
    MemoryDocument,
    MemoryOverview,
    ResearchRunCreate,
    RunRecord,
    RunStatus,
    UpdateActionCreate,
    UpdatesOverview,
)
from .spaces import SpacesClient
from .storage import RunRepository, create_repository
from .updates import approved_update_to_workflow_notes, proposed_update_from_feedback
from .worker import process_research_run

settings = get_settings()
repository = create_repository(settings.database_url, settings.local_sqlite_path)

app = FastAPI(title="AI Research Agent Worker", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def authorize(
    authorization: Annotated[str | None, Header()] = None,
    x_agent_backend_token: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.agent_backend_token:
        return
    expected = settings.agent_backend_token
    bearer = authorization.removeprefix("Bearer ").strip() if authorization else None
    if bearer != expected and x_agent_backend_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def authorize_update(passcode: str | None) -> None:
    if not settings.admin_update_passcode:
        return
    if passcode != settings.admin_update_passcode:
        raise HTTPException(status_code=401, detail="Invalid admin update passcode")


def spaces_client() -> SpacesClient:
    return SpacesClient(
        bucket=settings.do_spaces_bucket,
        region=settings.do_spaces_region,
        endpoint=settings.do_spaces_endpoint,
        access_key_id=settings.do_spaces_access_key_id,
        secret_access_key=settings.do_spaces_secret_access_key,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-research-agent-worker"}


@app.get("/runs", response_model=list[RunRecord], response_model_by_alias=True)
async def list_runs(_: None = Depends(authorize)) -> list[RunRecord]:
    return repository.list_runs()


@app.post("/runs", response_model=RunRecord, response_model_by_alias=True)
async def create_run(
    payload: ResearchRunCreate,
    background_tasks: BackgroundTasks,
    _: None = Depends(authorize),
) -> RunRecord:
    run = repository.create_run(payload.intake)
    background_tasks.add_task(process_research_run, run.id, repository, settings)
    return run


@app.get("/runs/{run_id}", response_model=RunRecord, response_model_by_alias=True)
async def get_run(run_id: str, _: None = Depends(authorize)) -> RunRecord:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/runs/{run_id}/cancel", response_model=ActionResponse, response_model_by_alias=True)
async def cancel_run(run_id: str, _: None = Depends(authorize)) -> ActionResponse:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in {RunStatus.completed, RunStatus.failed}:
        return ActionResponse(runId=run_id, status=run.status, message="Run has already finished.")
    repository.update_run(run_id, status=RunStatus.canceled)
    repository.append_event(run_id, "run_canceled", "Run canceled by user.")
    return ActionResponse(runId=run_id, status=RunStatus.canceled, message="Run canceled.")


@app.post("/runs/{run_id}/retry", response_model=ActionResponse, response_model_by_alias=True)
async def retry_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(authorize),
) -> ActionResponse:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    repository.update_run(run_id, status=RunStatus.queued, error=None)
    repository.append_event(run_id, "run_retry_requested", "Retry requested by user.")
    background_tasks.add_task(process_research_run, run_id, repository, settings)
    return ActionResponse(runId=run_id, status=RunStatus.queued, message="Run queued for retry.")


@app.post("/runs/{run_id}/resume", response_model=ActionResponse, response_model_by_alias=True)
async def resume_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    _: None = Depends(authorize),
) -> ActionResponse:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    repository.append_event(run_id, "run_resume_requested", "Resume requested by user.")
    background_tasks.add_task(process_research_run, run_id, repository, settings)
    return ActionResponse(runId=run_id, status=run.status, message="Resume requested.")


@app.post("/runs/{run_id}/feedback", response_model=ActionResponse, response_model_by_alias=True)
async def save_feedback(
    run_id: str,
    feedback: FeedbackCreate,
    _: None = Depends(authorize),
) -> ActionResponse:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    repository.save_feedback(run_id, feedback)
    title, category, body = proposed_update_from_feedback(run, feedback)
    proposed_update = repository.create_proposed_update(
        title=title,
        category=category,
        body=body,
        evidence_run_ids=[run_id],
    )
    run.progress.proposed_update_count += 1
    repository.update_run(run_id, progress=run.progress)
    repository.append_event(
        run_id,
        "feedback_saved",
        "Feedback saved and converted into a pending proposed update.",
        {"proposed_update_id": proposed_update.id, "category": proposed_update.category},
    )
    return ActionResponse(
        runId=run_id,
        status=run.status,
        message="Feedback saved and queued as a proposed update.",
    )


@app.get("/updates", response_model=UpdatesOverview, response_model_by_alias=True)
async def list_updates(_: None = Depends(authorize)) -> UpdatesOverview:
    return UpdatesOverview(
        proposedUpdates=repository.list_proposed_updates(),
        workflowVersions=repository.list_workflow_versions(),
        updateApplications=repository.list_update_applications(),
    )


@app.post("/updates/{update_id}/approve", response_model=ActionResponse, response_model_by_alias=True)
async def approve_update(
    update_id: str,
    payload: UpdateActionCreate,
    _: None = Depends(authorize),
) -> ActionResponse:
    authorize_update(payload.passcode)
    update = repository.set_proposed_update_status(update_id, "approved")
    notes, source_policy = approved_update_to_workflow_notes(
        update.title,
        update.category,
        update.body,
    )
    if update.category in {"instructions", "source_policy", "workflow", "user_preference", "evaluation"}:
        workflow = repository.create_workflow_version(
            version=f"research-workflow-{update.id}",
            notes=notes,
            instruction_summary=update.body[:900],
            source_policy=source_policy,
        )
        workflow_version = workflow.version
    else:
        workflow_version = None
    sync_result = sync_approved_update_to_spaces(
        spaces_client(),
        update,
        workflow_version=workflow_version,
    )
    repository.create_update_application(
        update_id=update.id,
        category=update.category,
        status=sync_result["status"] or "runtime_applied",
        summary=sync_result["summary"] or "Approved update processed.",
        memory_key=sync_result.get("memory_key"),
        artifact_key=sync_result.get("artifact_key"),
        workflow_version=workflow_version,
    )
    return ActionResponse(status=update.status, message="Update approved and versioned.")


@app.post("/updates/{update_id}/decline", response_model=ActionResponse, response_model_by_alias=True)
async def decline_update(
    update_id: str,
    payload: UpdateActionCreate,
    _: None = Depends(authorize),
) -> ActionResponse:
    authorize_update(payload.passcode)
    update = repository.set_proposed_update_status(update_id, "declined")
    repository.create_update_application(
        update_id=update.id,
        category=update.category,
        status="declined",
        summary="Update declined by admin.",
    )
    return ActionResponse(status=update.status, message="Update declined.")


@app.get("/memory", response_model=MemoryOverview, response_model_by_alias=True)
async def get_memory(_: None = Depends(authorize)) -> MemoryOverview:
    return load_memory_overview(
        spaces_client(),
        update_applications=repository.list_update_applications(),
    )


@app.get("/memory/{key:path}", response_model=MemoryDocument, response_model_by_alias=True)
async def get_memory_document(key: str, _: None = Depends(authorize)) -> MemoryDocument:
    if not key.startswith(("instructions/", "tool-configs/", "workflows/", "evals/", "backlog/")):
        raise HTTPException(status_code=400, detail="Memory key is not readable through this endpoint.")
    content = spaces_client().get_text(key)
    if content is None:
        raise HTTPException(status_code=404, detail="Memory document not found")
    return MemoryDocument(
        key=key,
        title=key.rsplit("/", 1)[-1],
        category=_memory_category_for_key(key),
        summary="Memory document loaded from DigitalOcean Spaces.",
        content=content,
        status="active",
        updatedAt=None,
    )


@app.post("/memory/bootstrap", response_model=MemoryOverview, response_model_by_alias=True)
async def bootstrap_memory_endpoint(
    payload: UpdateActionCreate,
    _: None = Depends(authorize),
) -> MemoryOverview:
    authorize_update(payload.passcode)
    overview = bootstrap_memory(spaces_client())
    overview.update_applications = repository.list_update_applications()
    return overview


@app.get("/evals", response_model=EvalsOverview, response_model_by_alias=True)
async def list_evals(_: None = Depends(authorize)) -> EvalsOverview:
    return EvalsOverview(
        cases=list_evaluation_cases(spaces_client()),
        results=repository.list_evaluation_results(),
    )


@app.post("/evals/run", response_model=EvalsOverview, response_model_by_alias=True)
async def run_evals(
    payload: EvalRunCreate,
    _: None = Depends(authorize),
) -> EvalsOverview:
    authorize_update(payload.passcode)
    run = repository.get_run(payload.run_id) if payload.run_id else _latest_completed_run()
    cases = list_evaluation_cases(spaces_client())
    results = run_quality_evaluations(
        run_id=run.id if run else payload.run_id,
        report_markdown=run.result_markdown if run else None,
        cases=cases,
    )
    saved_results = save_evaluation_results(
        spaces_client(),
        run_id=run.id if run else payload.run_id,
        results=results,
    )
    repository.save_evaluation_results(saved_results)
    return EvalsOverview(cases=cases, results=repository.list_evaluation_results())


def _latest_completed_run() -> RunRecord | None:
    return next((run for run in repository.list_runs() if run.status == RunStatus.completed), None)


def _memory_category_for_key(key: str):
    if key.startswith("tool-configs/"):
        return "tool_config"
    if key.startswith("workflows/"):
        return "workflow"
    if key.startswith("evals/"):
        return "evaluation"
    if key.startswith("backlog/"):
        return "backlog"
    if "source-policy" in key:
        return "source_policy"
    if "notion-formatting" in key:
        return "notion_formatting"
    if "learning" in key:
        return "learning_output"
    if "approved" in key:
        return "approved_update"
    return "instructions"


def main() -> None:
    uvicorn.run("ai_research_agent.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(main))
