from __future__ import annotations

from .schemas import (
    EvaluationResult,
    FeedbackCreate,
    ProposedUpdate,
    RunRecord,
    UpdateCategory,
    UpdateEvidenceSummary,
)


def proposed_update_from_feedback(run: RunRecord, feedback: FeedbackCreate) -> tuple[str, UpdateCategory, str]:
    comment = feedback.comment or ""
    topic = run.intake.niche_research_topic
    category = _classify_feedback(comment)
    title = _title_for_category(category, topic)
    body = (
        f"Feedback from run {run.id} on '{topic}':\n\n"
        f"{comment.strip() or feedback.rating or 'No written comment provided.'}\n\n"
        "Recommended handling: keep this as a pending recommendation until an admin approves it. "
        "If approved, apply it as a versioned workflow, source-policy, formatting, preference, "
        "evaluation, or UI backlog update depending on category."
    )
    return title, category, body


def approved_update_to_workflow_notes(title: str, category: UpdateCategory, body: str) -> tuple[str, str | None]:
    if category == "source_policy":
        return (
            f"Approved source-policy update: {title}",
            _compact(body),
        )
    if category in {
        "instructions",
        "workflow",
        "notion_formatting",
        "user_preference",
        "evaluation",
    }:
        return (
            f"Approved runtime update: {title}",
            None,
        )
    return (
        f"Approved backlog update: {title}",
        None,
    )


def summarize_update_evidence(
    updates: list[ProposedUpdate],
    evaluation_results: list[EvaluationResult],
) -> list[UpdateEvidenceSummary]:
    summaries: list[UpdateEvidenceSummary] = []
    for update in updates:
        evidence_run_ids = update.evidence_run_ids
        matching_results = [
            result
            for result in evaluation_results
            if result.run_id is not None and result.run_id in evidence_run_ids
        ]
        pass_count = sum(1 for result in matching_results if result.status == "pass")
        warning_count = sum(1 for result in matching_results if result.status == "warning")
        fail_count = sum(1 for result in matching_results if result.status == "fail")
        evaluated_run_ids = sorted({result.run_id for result in matching_results if result.run_id})
        latest_result_at = max((result.created_at for result in matching_results), default=None)
        status = _evidence_status(
            eval_result_count=len(matching_results),
            warning_count=warning_count,
            fail_count=fail_count,
        )
        summaries.append(
            UpdateEvidenceSummary(
                updateId=update.id,
                evidenceRunIds=evidence_run_ids,
                evaluatedRunIds=evaluated_run_ids,
                evalResultCount=len(matching_results),
                passCount=pass_count,
                warningCount=warning_count,
                failCount=fail_count,
                status=status,
                summary=_evidence_summary_text(
                    evidence_run_count=len(evidence_run_ids),
                    eval_result_count=len(matching_results),
                    pass_count=pass_count,
                    warning_count=warning_count,
                    fail_count=fail_count,
                ),
                latestResultAt=latest_result_at,
            )
        )
    return summaries


def _classify_feedback(comment: str) -> UpdateCategory:
    lower = comment.lower()
    if any(term in lower for term in ["youtube", "source", "citation", "credible", "trust"]):
        return "source_policy"
    if any(term in lower for term in ["notion", "bold", "list", "format", "code block", "title"]):
        return "notion_formatting"
    if any(term in lower for term in ["progress", "button", "ui", "interface", "screen", "preview"]):
        return "ui"
    if any(term in lower for term in ["too basic", "too advanced", "preference", "skill"]):
        return "user_preference"
    if any(term in lower for term in ["test", "eval", "regression"]):
        return "evaluation"
    if any(term in lower for term in ["workflow", "loop", "phase"]):
        return "workflow"
    return "instructions"


def _title_for_category(category: UpdateCategory, topic: str) -> str:
    labels = {
        "instructions": "Instruction update",
        "source_policy": "Source policy update",
        "workflow": "Workflow update",
        "notion_formatting": "Notion formatting update",
        "ui": "UI backlog update",
        "user_preference": "User preference update",
        "evaluation": "Evaluation update",
        "code_backlog": "Code backlog update",
    }
    return f"{labels[category]} for {topic[:60]}"


def _compact(text: str) -> str:
    return " ".join(text.split())[:900]


def _evidence_status(*, eval_result_count: int, warning_count: int, fail_count: int) -> str:
    if eval_result_count == 0:
        return "missing"
    if fail_count:
        return "fail"
    if warning_count:
        return "warning"
    return "pass"


def _evidence_summary_text(
    *,
    evidence_run_count: int,
    eval_result_count: int,
    pass_count: int,
    warning_count: int,
    fail_count: int,
) -> str:
    if eval_result_count == 0:
        if evidence_run_count == 0:
            return "No evidence runs are attached to this update yet."
        return "Evidence runs exist, but no eval results have been recorded for them yet."
    return (
        f"{eval_result_count} eval result(s): "
        f"{pass_count} pass, {warning_count} warning, {fail_count} fail."
    )
