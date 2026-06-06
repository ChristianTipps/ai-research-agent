from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import re
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    checkpoint_saved = "checkpoint_saved"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class WorkflowPhase(StrEnum):
    intake_validation = "intake_validation"
    intake_normalization = "intake_normalization"
    prior_knowledge_retrieval = "prior_knowledge_retrieval"
    source_strategy = "source_strategy"
    source_discovery = "source_discovery"
    source_review = "source_review"
    synthesis = "synthesis"
    report_formatting = "report_formatting"
    notion_save = "notion_save"
    digitalocean_save = "digitalocean_save"
    self_audit = "self_audit"
    final_delivery = "final_delivery"


DepthPreset = Literal[
    "Quick scan",
    "Standard brief",
    "Deep research",
    "Technical deep dive",
    "Custom",
]

SourceType = Literal[
    "official",
    "primary",
    "documentation",
    "research_paper",
    "github",
    "news",
    "community",
    "youtube",
    "web",
]

TranscriptStatus = Literal[
    "not_applicable",
    "available",
    "transcript_unavailable",
    "not_attempted",
]

ArtifactKind = Literal[
    "final_report",
    "run_summary",
    "source_artifact",
    "youtube_transcript",
    "trust_report",
    "workflow_version",
    "instruction_snapshot",
]

UpdateCategory = Literal[
    "instructions",
    "source_policy",
    "workflow",
    "notion_formatting",
    "ui",
    "user_preference",
    "evaluation",
    "code_backlog",
]

UpdateStatus = Literal["pending", "approved", "declined"]


class ResearchIntake(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    niche_research_topic: str = Field(alias="nicheResearchTopic", min_length=1)
    why_i_care: str = Field(alias="whyICare", min_length=1)
    intended_use: str = Field(alias="intendedUse", min_length=1)
    depth: DepthPreset
    custom_depth: str | None = Field(default=None, alias="customDepth")
    current_skill_level: str | None = Field(default=None, alias="currentSkillLevel")
    deadline: str | None = None
    research_budget_minutes: int | None = Field(
        default=None,
        alias="researchBudgetMinutes",
        ge=1,
        le=60,
    )
    output_type: str | None = Field(default=None, alias="outputType")
    youtube_urls: list[str] = Field(
        default_factory=list,
        alias="youtubeUrls",
        max_length=12,
    )

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("youtube_urls", mode="before")
    @classmethod
    def normalize_youtube_urls(cls, value: Any) -> list[str]:
        return _normalize_youtube_urls(value)

    @model_validator(mode="after")
    def require_custom_depth_when_custom(self) -> "ResearchIntake":
        if self.depth == "Custom" and not self.custom_depth:
            raise ValueError("customDepth is required when depth is Custom")
        return self


class ResearchRunCreate(BaseModel):
    intake: ResearchIntake


def _normalize_youtube_urls(value: Any) -> list[str]:
    if value is None or value == "":
        return []

    raw_values = value if isinstance(value, list) else [value]
    urls: list[str] = []
    for raw in raw_values:
        if raw is None:
            continue
        text = str(raw)
        candidates = re.findall(
            r"https?://[^\s,]+|www\.youtube\.com/[^\s,]+|youtube\.com/[^\s,]+|youtu\.be/[^\s,]+",
            text,
            flags=re.I,
        )
        if not candidates:
            candidates = re.split(r"[\s,]+", text)
        for candidate in candidates:
            url = _clean_youtube_url(candidate)
            if url:
                urls.append(url)

    result: list[str] = []
    seen: set[str] = set()
    for url in urls:
        key = url.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        result.append(url)
    return result


def _clean_youtube_url(value: str) -> str | None:
    candidate = value.strip().strip("()[]{}<>.,;\"'")
    if not candidate:
        return None
    if candidate.startswith("www."):
        candidate = f"https://{candidate}"
    elif candidate.startswith(("youtube.com/", "youtu.be/")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
        return None
    return candidate


class WorkflowStep(BaseModel):
    key: WorkflowPhase
    label: str
    status: Literal["pending", "active", "done", "blocked", "failed"]
    summary: str | None = None


class SourceRecord(BaseModel):
    id: str
    title: str
    url: str | None = None
    source_type: SourceType = Field(default="web", alias="sourceType")
    author: str | None = None
    channel_name: str | None = Field(default=None, alias="channelName")
    published_date: str | None = Field(default=None, alias="publishedDate")
    confidence: Literal["high", "medium", "low"]
    confidence_reason: str | None = Field(default=None, alias="confidenceReason")
    relevance: str | None = None
    transcript_status: TranscriptStatus = Field(
        default="not_applicable",
        alias="transcriptStatus",
    )
    artifact_key: str | None = Field(default=None, alias="artifactKey")
    notes: str | None = None


class SourceStrategy(BaseModel):
    requested_source_types: list[SourceType] = Field(
        default_factory=list,
        alias="requestedSourceTypes",
    )
    required_source_types: list[SourceType] = Field(
        default_factory=list,
        alias="requiredSourceTypes",
    )
    source_targets: list[str] = Field(default_factory=list, alias="sourceTargets")
    min_sources: int = Field(default=5, alias="minSources")
    max_sources: int = Field(default=10, alias="maxSources")
    include_youtube: bool = Field(default=False, alias="includeYouTube")
    rationale: str = "Use topic-aware source diversity."


class ArtifactRecord(BaseModel):
    id: str
    kind: ArtifactKind
    label: str
    key: str
    url: str | None = None
    content_type: str = Field(default="application/json", alias="contentType")
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")


class TrustReport(BaseModel):
    overall_confidence: Literal["high", "medium", "low"] = Field(
        alias="overallConfidence"
    )
    summary: str
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_mix: list[str] = Field(default_factory=list, alias="sourceMix")
    recommendations: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    id: str
    title: str
    body: str
    status: Literal["pending", "approved", "declined"] = "pending"


class SavedLocations(BaseModel):
    notion_prompt_url: str | None = Field(default=None, alias="notionPromptUrl")
    notion_response_url: str | None = Field(default=None, alias="notionResponseUrl")
    spaces_summary_key: str | None = Field(default=None, alias="spacesSummaryKey")
    final_report_key: str | None = Field(default=None, alias="finalReportKey")
    trust_report_key: str | None = Field(default=None, alias="trustReportKey")


class RunProgress(BaseModel):
    timeline: list[WorkflowStep]
    phase_message: str = Field(default="Queued.", alias="phaseMessage")
    progress_percent: int = Field(default=0, alias="progressPercent")
    source_strategy: SourceStrategy | None = Field(default=None, alias="sourceStrategy")
    source_records: list[SourceRecord] = Field(default_factory=list, alias="sourceRecords")
    artifact_records: list[ArtifactRecord] = Field(default_factory=list, alias="artifactRecords")
    trust_report: TrustReport | None = Field(default=None, alias="trustReport")
    tool_summaries: list[str] = Field(default_factory=list, alias="toolSummaries")
    decision_log: list[str] = Field(default_factory=list, alias="decisionLog")
    approval_requests: list[ApprovalRequest] = Field(default_factory=list, alias="approvalRequests")
    saved_locations: SavedLocations = Field(default_factory=SavedLocations, alias="savedLocations")
    workflow_version: str = Field(default="research-workflow-v1", alias="workflowVersion")
    proposed_update_count: int = Field(default=0, alias="proposedUpdateCount")


class RunRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: RunStatus
    phase: WorkflowPhase
    requested_depth: str = Field(alias="requestedDepth")
    intake: ResearchIntake
    progress: RunProgress
    result_markdown: str | None = Field(default=None, alias="resultMarkdown")
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class FeedbackCreate(BaseModel):
    rating: str | None = None
    comment: str | None = None


class ProposedUpdate(BaseModel):
    id: str
    title: str
    category: UpdateCategory
    status: UpdateStatus = "pending"
    body: str
    evidence_run_ids: list[str] = Field(default_factory=list, alias="evidenceRunIds")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    approved_at: datetime | None = Field(default=None, alias="approvedAt")
    declined_at: datetime | None = Field(default=None, alias="declinedAt")


class WorkflowVersion(BaseModel):
    id: str
    version: str
    status: Literal["active", "archived", "proposed"] = "active"
    notes: str
    instruction_summary: str | None = Field(default=None, alias="instructionSummary")
    source_policy: str | None = Field(default=None, alias="sourcePolicy")
    created_at: datetime = Field(alias="createdAt")
    approved_at: datetime | None = Field(default=None, alias="approvedAt")


class UpdatesOverview(BaseModel):
    proposed_updates: list[ProposedUpdate] = Field(alias="proposedUpdates")
    workflow_versions: list[WorkflowVersion] = Field(alias="workflowVersions")


class UpdateActionCreate(BaseModel):
    passcode: str | None = None


class ActionResponse(BaseModel):
    run_id: str | None = Field(default=None, alias="runId")
    status: RunStatus | UpdateStatus
    message: str


REQUIRED_FIELD_LABELS = {
    "nicheResearchTopic": "Research topic",
    "whyICare": "Why it matters",
    "intendedUse": "Intended use",
    "depth": "Research depth",
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def initial_progress() -> RunProgress:
    labels = {
        WorkflowPhase.intake_validation: "Intake validation",
        WorkflowPhase.intake_normalization: "Intake normalization",
        WorkflowPhase.prior_knowledge_retrieval: "Memory and instructions",
        WorkflowPhase.source_strategy: "Source strategy",
        WorkflowPhase.source_discovery: "Source discovery",
        WorkflowPhase.source_review: "Source review",
        WorkflowPhase.synthesis: "Synthesis",
        WorkflowPhase.report_formatting: "Report formatting",
        WorkflowPhase.notion_save: "Notion save",
        WorkflowPhase.digitalocean_save: "DigitalOcean save",
        WorkflowPhase.self_audit: "Self-audit",
        WorkflowPhase.final_delivery: "Final delivery",
    }
    return RunProgress(
        timeline=[
            WorkflowStep(key=phase, label=label, status="pending")
            for phase, label in labels.items()
        ]
    )
