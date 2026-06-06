from __future__ import annotations

import asyncio
import uuid
from typing import Any

from .agent import run_research_agent
from .config import Settings
from .formatting import prepare_final_report
from .notion import NotionClient
from .progress import complete_progress, mark_phase
from .schemas import ArtifactRecord, RunStatus, SourceRecord, TrustReport, WorkflowPhase
from .source_strategy import (
    build_source_strategy,
    build_trust_report,
    resolve_research_budget_minutes,
    review_source_record,
)
from .sources import extract_sources
from .spaces import SpacesClient, dated_artifact_key
from .storage import RunRepository
from .youtube import collect_youtube_artifact


def append_saved_records_section(
    markdown: str,
    *,
    notion_prompt_url: str | None,
    notion_response_url: str | None,
    spaces_summary_key: str | None,
    final_report_key: str | None,
    trust_report_key: str | None,
) -> str:
    prompt_status = notion_prompt_url or "Not saved. Notion is not configured or saving failed."
    response_status = notion_response_url or "Not saved. Notion is not configured or saving failed."
    spaces_status = spaces_summary_key or "Not saved. DigitalOcean Spaces is not configured or saving failed."
    final_status = final_report_key or "Not saved. DigitalOcean Spaces is not configured or saving failed."
    trust_status = trust_report_key or "Not saved. DigitalOcean Spaces is not configured or saving failed."
    return (
        markdown.rstrip()
        + "\n\n# 11. Saved records\n"
        + f"- Prompt saved to Notion: {prompt_status}\n"
        + f"- Research response saved to Notion: {response_status}\n"
        + "- Operational metadata saved to DigitalOcean backend: yes, run record updated.\n"
        + f"- DigitalOcean Spaces run summary: {spaces_status}\n"
        + f"- DigitalOcean Spaces final report: {final_status}\n"
        + f"- DigitalOcean Spaces trust report: {trust_status}\n"
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
        if run is None or run.status == RunStatus.canceled:
            return

        await _phase(
            repository,
            run_id,
            WorkflowPhase.intake_validation,
            "Required intake fields are present.",
            status=RunStatus.running,
        )

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

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.intake_normalization,
            "Normalized deadline as urgency and research budget as effort target.",
        )
        if run is None:
            return
        budget = resolve_research_budget_minutes(run.intake)
        run.intake.research_budget_minutes = budget
        run.progress.decision_log.append(
            f"Research budget interpreted as an effort target of {budget} minutes, not a hard wait timer."
        )
        repository.update_run(run_id, progress=run.progress)

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.prior_knowledge_retrieval,
            "Loaded approved update notes and active workflow context.",
        )
        if run is None:
            return
        approved_context = _approved_update_context(repository)
        if approved_context:
            run.progress.tool_summaries.append("Approved update notes loaded into the research prompt.")
        else:
            run.progress.tool_summaries.append("No approved update notes are active yet.")
        repository.update_run(run_id, progress=run.progress)

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.source_strategy,
            "Built topic-aware source strategy before synthesis.",
        )
        if run is None:
            return
        strategy = build_source_strategy(run.intake)
        run.progress.source_strategy = strategy
        run.progress.tool_summaries.append(
            f"Source targets: {', '.join(strategy.source_targets)}."
        )
        repository.update_run(run_id, progress=run.progress)

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.source_discovery,
            "Running research with OpenAI hosted web search and the planned source mix.",
        )
        if run is None:
            return
        raw_agent_markdown = await run_research_agent(
            run.intake,
            model=settings.openai_model,
            enable_web_search=settings.enable_openai_web_search,
            source_strategy=strategy,
            approved_update_context=approved_context,
        )

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.source_review,
            "Extracting, typing, and reviewing sources before final formatting.",
        )
        if run is None:
            return
        sources = [review_source_record(source) for source in extract_sources(raw_agent_markdown)]
        youtube_artifacts = await _collect_youtube_sources(sources)
        artifacts: list[ArtifactRecord] = []
        for source in sources:
            artifact = _source_artifact_record(source, run_id)
            source.artifact_key = artifact.key
            artifacts.append(artifact)
        artifacts.extend(_youtube_artifact_records(youtube_artifacts, run_id, sources))
        if sources:
            repository.add_sources(run_id, sources)
            run.progress.source_records = sources
        run.progress.artifact_records.extend(artifacts)
        repository.update_run(run_id, progress=run.progress)

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.synthesis,
            "Synthesis completed; preparing final learning report.",
        )
        if run is None:
            return
        agent_markdown = prepare_final_report(raw_agent_markdown, sources)

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.report_formatting,
            "Final report formatted with source links gathered at the end.",
        )
        if run is None:
            return
        trust_report = build_trust_report(sources, strategy)
        run.progress.trust_report = trust_report
        repository.save_trust_report(run_id, trust_report)
        repository.update_run(run_id, progress=run.progress)

        run = await _phase(repository, run_id, WorkflowPhase.notion_save, "Saving final response.")
        if run is None:
            return
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

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.digitalocean_save,
            "Saving artifacts, source notes, trust report, and run summary.",
        )
        if run is None:
            return
        spaces_keys = _save_spaces_artifacts(
            spaces,
            run_id,
            final_markdown=agent_markdown,
            sources=sources,
            source_artifacts=artifacts,
            youtube_artifacts=youtube_artifacts,
            trust_report=trust_report,
            run_summary=_spaces_summary(run),
        )
        saved_artifacts = spaces_keys["artifacts"]
        if saved_artifacts:
            run.progress.artifact_records = saved_artifacts
            repository.add_artifacts(run_id, saved_artifacts)
        repository.save_locations(
            run_id,
            spaces_summary_key=spaces_keys.get("summary_key"),
            final_report_key=spaces_keys.get("final_report_key"),
            trust_report_key=spaces_keys.get("trust_report_key"),
        )
        repository.append_event(
            run_id,
            "spaces_artifacts_saved" if spaces_keys.get("summary_key") else "spaces_artifacts_skipped",
            "DigitalOcean Spaces artifact save attempted.",
        )

        run = await _phase(
            repository,
            run_id,
            WorkflowPhase.self_audit,
            "Trust report and artifact persistence reviewed.",
        )
        if run is None:
            return
        run.progress.trust_report = trust_report
        run.progress.tool_summaries.append(
            f"Trust self-report: {trust_report.overall_confidence} confidence."
        )
        repository.update_run(run_id, progress=run.progress)

        run = repository.get_run(run_id)
        final_markdown = append_saved_records_section(
            agent_markdown,
            notion_prompt_url=run.progress.saved_locations.notion_prompt_url if run else prompt_url,
            notion_response_url=run.progress.saved_locations.notion_response_url if run else response_url,
            spaces_summary_key=run.progress.saved_locations.spaces_summary_key if run else None,
            final_report_key=run.progress.saved_locations.final_report_key if run else None,
            trust_report_key=run.progress.saved_locations.trust_report_key if run else None,
        )
        progress = complete_progress(run.progress if run else initial_progress())
        progress.progress_percent = 100
        progress.phase_message = "Final report delivered."
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
            failed_progress = mark_phase(run.progress, run.phase, failed=True, message=str(exc))
            repository.update_run(
                run_id,
                status=RunStatus.failed,
                progress=failed_progress,
                error=str(exc),
            )
        repository.append_event(run_id, "run_failed", str(exc))


async def _phase(
    repository: RunRepository,
    run_id: str,
    phase: WorkflowPhase,
    summary: str,
    *,
    status: RunStatus = RunStatus.running,
) -> Any | None:
    await asyncio.sleep(0)
    run = repository.get_run(run_id)
    if run is None or run.status == RunStatus.canceled:
        return None
    progress = mark_phase(run.progress, phase, message=summary)
    progress.tool_summaries.append(summary)
    updated = repository.update_run(run_id, status=status, phase=phase, progress=progress)
    repository.append_event(run_id, phase.value, summary)
    return updated


async def _collect_youtube_sources(sources: list[SourceRecord]) -> list[Any]:
    artifacts = []
    for source in sources:
        if source.source_type != "youtube":
            continue
        artifact = await collect_youtube_artifact(source)
        if artifact is None:
            source.transcript_status = "transcript_unavailable"
            source.notes = _append_note(source.notes, "YouTube metadata/transcript lookup did not return a video artifact.")
            continue
        if artifact.metadata.get("title"):
            source.title = artifact.metadata["title"]
        if artifact.metadata.get("author_name"):
            source.channel_name = artifact.metadata["author_name"]
            source.author = artifact.metadata["author_name"]
        source.transcript_status = artifact.transcript_status  # type: ignore[assignment]
        source.notes = _append_note(
            source.notes,
            "Best-effort public transcript was available."
            if artifact.transcript
            else "Best-effort public transcript was unavailable.",
        )
        artifacts.append(artifact)
    return artifacts


def _save_spaces_artifacts(
    spaces: SpacesClient,
    run_id: str,
    *,
    final_markdown: str,
    sources: list[SourceRecord],
    source_artifacts: list[ArtifactRecord],
    youtube_artifacts: list[Any],
    trust_report: TrustReport,
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    saved_artifacts: list[ArtifactRecord] = []
    final_key = dated_artifact_key("knowledge-base", run_id, "final-report", "md")
    if spaces.save_markdown(final_key, final_markdown):
        saved_artifacts.append(
            ArtifactRecord(
                id=f"art_{uuid.uuid4().hex[:10]}",
                kind="final_report",
                label="Final report markdown",
                key=final_key,
                contentType="text/markdown",
                notes="Readable final report saved for durable knowledge-base reuse.",
            )
        )

    trust_key = dated_artifact_key("run-summaries", run_id, "trust-report", "json")
    if spaces.save_json(trust_key, trust_report.model_dump(by_alias=True)):
        saved_artifacts.append(
            ArtifactRecord(
                id=f"art_{uuid.uuid4().hex[:10]}",
                kind="trust_report",
                label="Trust self-report",
                key=trust_key,
                contentType="application/json",
                notes="Internal source-quality self-report.",
            )
        )

    for artifact in source_artifacts:
        source = next((item for item in sources if item.artifact_key == artifact.key), None)
        payload = source.model_dump(by_alias=True) if source else {"artifact": artifact.label}
        if spaces.save_json(artifact.key, payload):
            saved_artifacts.append(artifact)

    for youtube_artifact in youtube_artifacts:
        transcript_key = dated_artifact_key(
            "source-artifacts",
            run_id,
            f"{youtube_artifact.video_id}-transcript",
            "json",
        )
        payload = {
            "sourceId": youtube_artifact.source_id,
            "videoId": youtube_artifact.video_id,
            "metadata": youtube_artifact.metadata,
            "transcriptStatus": youtube_artifact.transcript_status,
            "transcript": youtube_artifact.transcript,
        }
        if spaces.save_json(transcript_key, payload):
            saved_artifacts.append(
                ArtifactRecord(
                    id=f"art_{uuid.uuid4().hex[:10]}",
                    kind="youtube_transcript",
                    label=f"YouTube transcript metadata for {youtube_artifact.video_id}",
                    key=transcript_key,
                    contentType="application/json",
                    notes="Best-effort public transcript artifact; may contain no transcript text.",
                )
            )

    workflow_key = "workflows/versions/research-workflow-v1.json"
    if spaces.save_json(
        workflow_key,
        {
            "version": "research-workflow-v1",
            "description": "Staged research workflow with source strategy, source review, trust report, and authorized updates.",
        },
    ):
        saved_artifacts.append(
            ArtifactRecord(
                id=f"art_{uuid.uuid4().hex[:10]}",
                kind="workflow_version",
                label="Active workflow version",
                key=workflow_key,
                contentType="application/json",
                notes="Workflow version snapshot saved to Spaces.",
            )
        )

    summary_key = spaces.save_run_summary(run_id, run_summary)
    if summary_key:
        saved_artifacts.append(
            ArtifactRecord(
                id=f"art_{uuid.uuid4().hex[:10]}",
                kind="run_summary",
                label="Run summary",
                key=summary_key,
                contentType="application/json",
                notes="Concise operational run summary.",
            )
        )

    return {
        "summary_key": summary_key,
        "final_report_key": final_key if any(item.key == final_key for item in saved_artifacts) else None,
        "trust_report_key": trust_key if any(item.key == trust_key for item in saved_artifacts) else None,
        "artifacts": saved_artifacts,
    }


def _source_artifact_record(source: SourceRecord, run_id: str) -> ArtifactRecord:
    key = dated_artifact_key("source-artifacts", run_id, source.id, "json")
    return ArtifactRecord(
        id=f"art_{uuid.uuid4().hex[:10]}",
        kind="source_artifact",
        label=source.title[:80] or source.id,
        key=key,
        contentType="application/json",
        notes="Source metadata and trust classification.",
    )


def _youtube_artifact_records(
    youtube_artifacts: list[Any],
    run_id: str,
    sources: list[SourceRecord],
) -> list[ArtifactRecord]:
    records: list[ArtifactRecord] = []
    for artifact in youtube_artifacts:
        key = dated_artifact_key("source-artifacts", run_id, f"{artifact.video_id}-metadata", "json")
        source = next((item for item in sources if item.id == artifact.source_id), None)
        records.append(
            ArtifactRecord(
                id=f"art_{uuid.uuid4().hex[:10]}",
                kind="source_artifact",
                label=f"YouTube metadata: {(source.title if source else artifact.video_id)[:60]}",
                key=key,
                contentType="application/json",
                notes=f"Transcript status: {artifact.transcript_status}.",
            )
        )
    return records


def _approved_update_context(repository: RunRepository) -> str:
    updates = repository.list_approved_runtime_updates()
    if not updates:
        return ""
    lines = []
    for update in updates:
        lines.append(f"- {update.category}: {update.title}. {update.body[:500]}")
    return "\n".join(lines)


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


def _append_note(existing: str | None, note: str) -> str:
    return f"{existing} {note}".strip() if existing else note
