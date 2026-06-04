from pydantic import ValidationError

from ai_research_agent.schemas import ResearchIntake, initial_progress


def test_required_intake_fields_are_validated() -> None:
    try:
        ResearchIntake(
            nicheResearchTopic="",
            whyICare="I want to build better agents",
            intendedUse="A learning dashboard",
            depth="Standard brief",
        )
    except ValidationError as exc:
        assert "nicheResearchTopic" in str(exc)
    else:
        raise AssertionError("Expected missing topic validation")


def test_custom_depth_requires_detail() -> None:
    try:
        ResearchIntake(
            nicheResearchTopic="Agent memory",
            whyICare="I am building a research agent",
            intendedUse="Implementation plan",
            depth="Custom",
        )
    except ValidationError as exc:
        assert "customDepth" in str(exc) or "custom_depth" in str(exc)
    else:
        raise AssertionError("Expected custom depth validation")


def test_initial_progress_has_workflow_steps() -> None:
    progress = initial_progress()
    assert progress.timeline[0].key == "intake_validation"
    assert progress.timeline[-1].key == "final_delivery"
