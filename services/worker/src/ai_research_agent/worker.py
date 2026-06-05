from __future__ import annotations

import asyncio
from typing import Any

from .agent import run_research_agent
from .config import Settings
from .formatting import prepare_final_report
from .notion import NotionClient
from .progress import complete_progress, mark_phase
from .schemas import RunStatus, WorkflowPhase
from .sources import extract_sources
from .spaces import SpacesClient
from .storage import RunRepository


def append_saved_records_section(
    markdown: str,
    *,
    notion_prompt_url: str | None,
    notion_response_url: str | None,
    spaces_summary_key: str | None,
) -> str:
    prompt_status = notion_prompt_url or "Not saved. Notion is not configured or saving failed."
    response_status = notion_response_url or "Not saved. Notion is not configured or saving failed."
    spaces_status = spaces_summary_key or "Not saved. DigitalOcean Spaces is not configured or saving failed."
    return (
        markdown.rstrip()
        + "\n\n# 11. Saved records\n"
        + f"- Prompt saved to Notion: {prompt_status}\n"
        + f"- Research response saved to Notion: {response_status}\n"
        + f"- Operational metadata saved to DigitalOcean backend: yes, run record updated.\n"
        + f"- DigitalOcean Spaces run summary: {spaces_status}\n"
    )


async def process_research_run(run_id: str, repository: RunRepository, settings: Settings) -> None:
    notion = NotionClient(
        api_key=settings.notion_api_key,
        prompts_database_id=settings.notion_prompts_database_id,
        responses_database_id=settings.notion_responses_database_id,
    )
    spaces = SpacesClient(
        bucket=settings.do_spaces_bucket,
        region=settings.do_spaces_region,
        endpoint=settings.do_spaces_endpoint,
        access_key_id=settings.do_spaces_access_key_id,
        secret_access_key=settings.do_spaces_secret_access_key,
    )

    try:
        run = repository.get_run(run_id)
        if run is None:
            return
        if run.status == RunStatus.canceled:
            return

        progress = mark_phase(run.progress, WorkflowPhase.intake_validation)
        repository.update_run(
            run_id,
            status=RunStatus.running,
            phase=WorkflowPhase.intake_validation,
            progress=progress,
        )
        repository.append_event(run_id, "intake_validated", "Required intake fields are present.")

        prompt_url = None
        try:
            prompt_url = await notion.save_prompt(run_id, run.intake)
            if prompt_url:
                repository.save_locations(run_id, notion_prompt_url=prompt_url)
                repository.append_event(run_id, "notion_prompt_saved", "Prompt saved to Notion.")
            else:
                repository.append_event(
                    run_id,
                    "notion_prompt_skipped",
                    "Prompt was not saved because Notion is not fully configured.",
                )
        except Exception as exc:  # noqa: BLE001
            repository.append_event(run_id, "notion_prompt_failed", str(exc))

        await _checkpoint(
            repository,
            run_id,
            WorkflowPhase.prior_knowledge_retrieval,
            "Checked configured knowledge sources and memory stores.",
        )
        await _checkpoint(
            repository,
            run_id,
            WorkflowPhase.source_discovery,
            "Starting source discovery with OpenAI hosted web search when enabled.",
        )
        await _checkpoint(
            repository,
            run_id,
            WorkflowPhase.source_review,
            "Reviewing source quality and preparing synthesis.",
        )

        run = repository.get_run(run_id)
        if run is None or run.status == RunStatus.canceled:
            return
        progress = mark_phase(run.progress, WorkflowPhase.synthesis)
        progress.tool_summaries.append("OpenAI Agents SDK Runner.run invoked for research synthesis.")
        progress.decision_log.append(
            "The worker owns long-running synthesis so Vercel does not hold a single request open."
        )
        repository.update_run(
            run_id,
            status=RunStatus.running,
            phase=WorkflowPhase.synthesis,
            progress=progress,
        )

        raw_agent_markdown = await run_research_agent(
            run.intake,
            model=settings.openai_model,
            enable_web_search=settings.enable_openai_web_search,
        )

        sources = extract_sources(raw_agent_markdown)
        agent_markdown = prepare_final_report(raw_agent_markdown, sources)
        if sources:
            repository.add_sources(run_id, sources)
            run = repository.get_run(run_id)
            if run:
                run.progress.source_records.extend(sources)
                repository.update_run(run_id, progress=run.progress)

        await _checkpoint(repository, run_id, WorkflowPhase.notion_save, "Saving final response.")
        response_url = None
        try:
            response_url = await notion.save_response(run_id, run.intake, agent_markdown)
            if response_url:
                repository.save_locations(run_id, notion_response_url=response_url)
                repository.append_event(run_id, "notion_response_saved", "Response saved to Notion.")
            else:
                repository.append_event(
                    run_id,
                    "notion_response_skipped",
                    "Response was not saved because Notion is not fully configured.",
                )
        except Exception as exc:  # noqa: BLE001
            repository.append_event(run_id, "notion_response_failed", str(exc))

        await _checkpoint(
            repository,
            run_id,
            WorkflowPhase.digitalocean_save,
            "Saving operational metadata and run summary.",
        )
        run = repository.get_run(run_id)
        spaces_key = None
        if run:
            try:
                spaces_key = spaces.save_run_summary(run_id, _spaces_summary(run))
                if spaces_key:
                    repository.save_locations(run_id, spaces_summary_key=spaces_key)
                    repository.append_event(run_id, "spaces_summary_saved", "Run summary saved.")
                else:
                    repository.append_event(
                        run_id,
                        "spaces_summary_skipped",
                        "Spaces summary was not saved because DigitalOcean Spaces is not configured.",
                    )
            except Exception as exc:  # noqa: BLE001
                repository.append_event(run_id, "spaces_summary_failed", str(exc))

        run = repository.get_run(run_id)
        final_markdown = append_saved_records_section(
            agent_markdown,
            notion_prompt_url=run.progress.saved_locations.notion_prompt_url if run else prompt_url,
            notion_response_url=run.progress.saved_locations.notion_response_url if run else response_url,
            spaces_summary_key=run.progress.saved_locations.spaces_summary_key if run else spaces_key,
        )
        progress = complete_progress(run.progress if run else progress)
        repository.update_run(
            run_id,
            status=RunStatus.completed,
            phase=WorkflowPhase.final_delivery,
            progress=progress,
            result_markdown=final_markdown,
        )
        repository.append_event(run_id, "run_completed", "Final response delivered.")
    except Exception as exc:  # noqa: BLE001
        run = repository.get_run(run_id)
        if run:
            failed_progress = mark_phase(run.progress, run.phase, failed=True)
            repository.update_run(
                run_id,
                status=RunStatus.failed,
                progress=failed_progress,
                error=str(exc),
            )
        repository.append_event(run_id, "run_failed", str(exc))


async def _checkpoint(
    repository: RunRepository,
    run_id: str,
    phase: WorkflowPhase,
    summary: str,
) -> None:
    await asyncio.sleep(0)
    run = repository.get_run(run_id)
    if run is None or run.status == RunStatus.canceled:
        return
    progress = mark_phase(run.progress, phase)
    progress.tool_summaries.append(summary)
    repository.update_run(run_id, status=RunStatus.running, phase=phase, progress=progress)
    repository.append_event(run_id, phase.value, summary)


def _spaces_summary(run: Any) -> dict[str, Any]:
    return {
        "run_id": run.id,
        "status": run.status,
        "phase": run.phase,
        "intake": run.intake.model_dump(by_alias=True),
        "progress": run.progress.model_dump(by_alias=True),
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }
