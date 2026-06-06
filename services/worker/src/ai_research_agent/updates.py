from __future__ import annotations

from .schemas import FeedbackCreate, RunRecord, UpdateCategory


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
    if category in {"instructions", "workflow", "user_preference", "evaluation"}:
        return (
            f"Approved runtime update: {title}",
            None,
        )
    return (
        f"Approved backlog update: {title}",
        None,
    )


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
