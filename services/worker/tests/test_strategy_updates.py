import json

from ai_research_agent.schemas import (
    ArtifactRecord,
    EvaluationResult,
    FeedbackCreate,
    ResearchIntake,
    initial_progress,
)
from ai_research_agent.agent import build_research_prompt
from ai_research_agent.memory import (
    bootstrap_memory,
    list_evaluation_cases,
    load_memory_context,
    run_quality_evaluations,
    sync_approved_update_to_spaces,
)
from ai_research_agent.source_strategy import build_source_strategy, resolve_research_budget_minutes
from ai_research_agent.storage import LocalSQLiteRunRepository
from ai_research_agent.updates import proposed_update_from_feedback, summarize_update_evidence
from ai_research_agent.youtube import extract_video_id


class FakeSpaces:
    bucket = "test"
    region = "sfo3"
    endpoint = "https://example.test"
    access_key_id = "access"
    secret_access_key = "secret"

    def __init__(self) -> None:
        self.objects: dict[str, str] = {}

    @property
    def enabled(self) -> bool:
        return True

    def object_exists(self, key: str) -> bool:
        return key in self.objects

    def save_text(self, key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
        self.objects[key] = text
        return key

    def save_markdown(self, key: str, markdown: str) -> str:
        self.objects[key] = markdown
        return key

    def save_json(self, key: str, payload):
        self.objects[key] = json.dumps(payload)
        return key

    def get_text(self, key: str):
        return self.objects.get(key)

    def get_json(self, key: str):
        value = self.objects.get(key)
        return json.loads(value) if value is not None else None


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


def test_user_supplied_youtube_urls_trigger_youtube_strategy() -> None:
    intake = ResearchIntake(
        nicheResearchTopic="Codex agent setup",
        whyICare="I want practical setup advice",
        intendedUse="Learning roadmap",
        depth="Standard brief",
        youtubeUrls=[
            "https://youtu.be/abc123XYZ",
            "https://www.youtube.com/watch?v=def456XYZ",
        ],
    )
    strategy = build_source_strategy(intake)

    assert intake.youtube_urls == [
        "https://youtu.be/abc123XYZ",
        "https://www.youtube.com/watch?v=def456XYZ",
    ]
    assert strategy.include_youtube is True
    assert "youtube" in strategy.required_source_types
    assert any("user-submitted YouTube" in target for target in strategy.source_targets)


def test_youtube_url_text_is_normalized_and_deduped() -> None:
    intake = ResearchIntake(
        nicheResearchTopic="Codex agent setup",
        whyICare="I want practical setup advice",
        intendedUse="Learning roadmap",
        depth="Standard brief",
        youtubeUrls="""
        https://youtu.be/abc123XYZ
        https://youtu.be/abc123XYZ,
        youtube.com/watch?v=def456XYZ
        https://example.com/not-youtube
        """,
    )

    assert intake.youtube_urls == [
        "https://youtu.be/abc123XYZ",
        "https://youtube.com/watch?v=def456XYZ",
    ]


def test_research_prompt_includes_seeded_youtube_context() -> None:
    intake = ResearchIntake(
        nicheResearchTopic="Codex agent setup",
        whyICare="I want practical setup advice",
        intendedUse="Learning roadmap",
        depth="Standard brief",
        youtubeUrls=["https://youtu.be/abc123XYZ"],
    )
    prompt = build_research_prompt(
        intake,
        seed_source_context="- Title: Example video\n  Transcript status: transcript_unavailable",
    )

    assert "User-provided YouTube source context" in prompt
    assert "Example video" in prompt
    assert "transcript_unavailable" in prompt


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


def test_notion_formatting_feedback_is_runtime_update(tmp_path) -> None:
    repo = LocalSQLiteRunRepository(str(tmp_path / "local.db"))
    run = repo.create_run(
        ResearchIntake(
            nicheResearchTopic="Notion report formatting",
            whyICare="Improve learning output",
            intendedUse="Feedback loop",
            depth="Standard brief",
        )
    )
    title, category, body = proposed_update_from_feedback(
        run,
        FeedbackCreate(comment="Keep bold text clean in Notion and fix numbered list formatting."),
    )
    update = repo.create_proposed_update(
        title=title,
        category=category,
        body=body,
        evidence_run_ids=[run.id],
    )

    assert update.category == "notion_formatting"
    approved = repo.set_proposed_update_status(update.id, "approved")

    assert approved.id in {item.id for item in repo.list_approved_runtime_updates()}


def test_progress_with_artifact_records_is_json_serializable() -> None:
    progress = initial_progress()
    progress.artifact_records.append(
        ArtifactRecord(
            id="art_test",
            kind="source_artifact",
            label="Test source",
            key="source-artifacts/test.json",
        )
    )

    json.dumps(progress.model_dump(by_alias=True, mode="json"))


def test_memory_bootstrap_is_idempotent_and_loads_context() -> None:
    spaces = FakeSpaces()
    bootstrap_memory(spaces)  # type: ignore[arg-type]
    spaces.objects["instructions/base.md"] = "custom approved base"
    bootstrap_memory(spaces)  # type: ignore[arg-type]

    assert spaces.objects["instructions/base.md"] == "custom approved base"
    assert "tool-configs/openai-web-search.json" in spaces.objects
    assert "workflows/versions/research-workflow-v1.json" in spaces.objects

    context = load_memory_context(spaces, approved_update_count=2)  # type: ignore[arg-type]
    assert context.approved_update_count == 2
    assert context.workflow_version == "research-workflow-v1"
    assert any(document.key == "instructions/base.md" for document in context.documents)


def test_approved_update_syncs_to_runtime_memory(tmp_path) -> None:
    repo = LocalSQLiteRunRepository(str(tmp_path / "local.db"))
    run = repo.create_run(
        ResearchIntake(
            nicheResearchTopic="Codex agents",
            whyICare="Improve my research agent",
            intendedUse="Feedback loop",
            depth="Standard brief",
        )
    )
    title, category, body = proposed_update_from_feedback(
        run,
        FeedbackCreate(comment="Use stronger source trust checks."),
    )
    update = repo.create_proposed_update(
        title=title,
        category=category,
        body=body,
        evidence_run_ids=[run.id],
    )
    update = repo.set_proposed_update_status(update.id, "approved")
    spaces = FakeSpaces()

    result = sync_approved_update_to_spaces(
        spaces,  # type: ignore[arg-type]
        update,
        workflow_version=f"research-workflow-{update.id}",
    )
    application = repo.create_update_application(
        update_id=update.id,
        category=update.category,
        status=result["status"] or "runtime_applied",
        summary=result["summary"] or "",
        memory_key=result["memory_key"],
        artifact_key=result["artifact_key"],
        workflow_version=f"research-workflow-{update.id}",
    )

    assert application.status == "runtime_applied"
    assert result["memory_key"] in spaces.objects
    assert repo.list_update_applications()[0].update_id == update.id
    assert repo.get_update_application_for_update(update.id).id == application.id


def test_update_evidence_summary_counts_eval_results(tmp_path) -> None:
    repo = LocalSQLiteRunRepository(str(tmp_path / "local.db"))
    run = repo.create_run(
        ResearchIntake(
            nicheResearchTopic="Codex agents",
            whyICare="Improve my research agent",
            intendedUse="Feedback loop",
            depth="Standard brief",
        )
    )
    title, category, body = proposed_update_from_feedback(
        run,
        FeedbackCreate(comment="Add better eval checks before approving source policy changes."),
    )
    update = repo.create_proposed_update(
        title=title,
        category=category,
        body=body,
        evidence_run_ids=[run.id],
    )
    results = [
        EvaluationResult(
            id="eval_pass",
            caseId="case_one",
            status="pass",
            score=1.0,
            summary="Required signals found.",
            runId=run.id,
            evidence=["signal"],
        ),
        EvaluationResult(
            id="eval_warning",
            caseId="case_two",
            status="warning",
            score=0.7,
            summary="Some optional signals were weak.",
            runId=run.id,
            evidence=["optional"],
        ),
    ]

    summary = summarize_update_evidence([update], results)[0]

    assert summary.update_id == update.id
    assert summary.status == "warning"
    assert summary.eval_result_count == 2
    assert summary.pass_count == 1
    assert summary.warning_count == 1
    assert summary.fail_count == 0
    assert summary.evaluated_run_ids == [run.id]


def test_eval_results_are_created_and_persisted(tmp_path) -> None:
    repo = LocalSQLiteRunRepository(str(tmp_path / "local.db"))
    spaces = FakeSpaces()
    bootstrap_memory(spaces)  # type: ignore[arg-type]
    cases = list_evaluation_cases(spaces)  # type: ignore[arg-type]
    results = run_quality_evaluations(
        run_id="run_test",
        report_markdown="# 1. Simple explanation\n\n# 5. Thesis, antithesis, and synthesis\n\n# 9. One small exercise and light quiz\n\n# 10. Sources and confidence\nConfidence: high.",
        cases=cases,
    )
    repo.save_evaluation_results(results)

    assert results
    saved_case_ids = {result.case_id for result in repo.list_evaluation_results()}
    assert {result.case_id for result in results} <= saved_case_ids
