from ai_research_agent.schemas import FeedbackCreate, ResearchIntake
from ai_research_agent.source_strategy import build_source_strategy, resolve_research_budget_minutes
from ai_research_agent.storage import LocalSQLiteRunRepository
from ai_research_agent.updates import proposed_update_from_feedback
from ai_research_agent.youtube import extract_video_id


def test_budget_defaults_and_custom_minutes() -> None:
    intake = ResearchIntake(
        nicheResearchTopic="Codex agents",
        whyICare="I am learning",
        intendedUse="Build plan",
        depth="Deep research",
    )
    assert resolve_research_budget_minutes(intake) == 10

    custom = ResearchIntake(
        nicheResearchTopic="Codex agents",
        whyICare="I am learning",
        intendedUse="Build plan",
        depth="Custom",
        customDepth="Take about 7 minutes and include examples",
    )
    assert resolve_research_budget_minutes(custom) == 7


def test_source_strategy_includes_youtube_when_requested() -> None:
    intake = ResearchIntake(
        nicheResearchTopic="Codex tutorials from YouTubers",
        whyICare="I want creator opinions and official facts",
        intendedUse="Learning roadmap",
        depth="Standard brief",
    )
    strategy = build_source_strategy(intake)

    assert strategy.include_youtube is True
    assert "youtube" in strategy.required_source_types
    assert strategy.min_sources >= 5


def test_youtube_video_id_detection() -> None:
    assert extract_video_id("https://www.youtube.com/watch?v=abc123XYZ") == "abc123XYZ"
    assert extract_video_id("https://youtu.be/abc123XYZ") == "abc123XYZ"
    assert extract_video_id("https://www.youtube.com/shorts/abc123XYZ") == "abc123XYZ"


def test_feedback_creates_pending_update_and_approval_versions(tmp_path) -> None:
    repo = LocalSQLiteRunRepository(str(tmp_path / "local.db"))
    run = repo.create_run(
        ResearchIntake(
            nicheResearchTopic="Codex agents",
            whyICare="Improve my research agent",
            intendedUse="Feedback loop",
            depth="Standard brief",
        )
    )
    feedback = FeedbackCreate(comment="Please include YouTube creator sources next time.")
    repo.save_feedback(run.id, feedback)
    title, category, body = proposed_update_from_feedback(run, feedback)
    update = repo.create_proposed_update(
        title=title,
        category=category,
        body=body,
        evidence_run_ids=[run.id],
    )

    assert update.status == "pending"
    assert update.category == "source_policy"

    approved = repo.set_proposed_update_status(update.id, "approved")
    assert approved.status == "approved"
    assert repo.list_approved_runtime_updates()[0].id == update.id
