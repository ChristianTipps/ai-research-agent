from __future__ import annotations

import asyncio
from typing import Annotated

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .schemas import ActionResponse, FeedbackCreate, ResearchRunCreate, RunRecord, RunStatus
from .storage import RunRepository, create_repository
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
    repository.append_event(run_id, "feedback_saved", "Feedback saved.")
    return ActionResponse(runId=run_id, status=run.status, message="Feedback saved.")


def main() -> None:
    uvicorn.run("ai_research_agent.main:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(main))
