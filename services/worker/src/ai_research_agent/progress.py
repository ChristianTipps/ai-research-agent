from __future__ import annotations

from .schemas import RunProgress, WorkflowPhase


def mark_phase(progress: RunProgress, phase: WorkflowPhase, failed: bool = False) -> RunProgress:
    seen_active = False
    for step in progress.timeline:
        if step.key == phase:
            step.status = "failed" if failed else "active"
            seen_active = True
        elif not seen_active and step.status in {"pending", "active"}:
            step.status = "done"
        elif seen_active and step.status == "active":
            step.status = "pending"
    return progress


def complete_progress(progress: RunProgress) -> RunProgress:
    for step in progress.timeline:
        if step.status != "failed":
            step.status = "done"
    return progress
