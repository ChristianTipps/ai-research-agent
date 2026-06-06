from __future__ import annotations

from .schemas import RunProgress, WorkflowPhase


PHASE_PERCENT = {
    WorkflowPhase.intake_validation: 5,
    WorkflowPhase.intake_normalization: 10,
    WorkflowPhase.prior_knowledge_retrieval: 18,
    WorkflowPhase.source_strategy: 26,
    WorkflowPhase.source_discovery: 38,
    WorkflowPhase.source_review: 52,
    WorkflowPhase.synthesis: 68,
    WorkflowPhase.report_formatting: 78,
    WorkflowPhase.notion_save: 86,
    WorkflowPhase.digitalocean_save: 92,
    WorkflowPhase.self_audit: 96,
    WorkflowPhase.final_delivery: 100,
}


def mark_phase(
    progress: RunProgress,
    phase: WorkflowPhase,
    failed: bool = False,
    message: str | None = None,
) -> RunProgress:
    seen_active = False
    for step in progress.timeline:
        if step.key == phase:
            step.status = "failed" if failed else "active"
            if message:
                step.summary = message
            seen_active = True
        elif not seen_active and step.status in {"pending", "active"}:
            step.status = "done"
        elif seen_active and step.status == "active":
            step.status = "pending"
    progress.phase_message = message or progress.phase_message
    progress.progress_percent = PHASE_PERCENT.get(phase, progress.progress_percent)
    return progress


def complete_progress(progress: RunProgress) -> RunProgress:
    for step in progress.timeline:
        if step.status != "failed":
            step.status = "done"
    return progress
