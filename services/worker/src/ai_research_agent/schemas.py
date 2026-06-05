from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

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
    prior_knowledge_retrieval = "prior_knowledge_retrieval"
    source_discovery = "source_discovery"
    source_review = "source_review"
    synthesis = "synthesis"
    notion_save = "notion_save"
    digitalocean_save = "digitalocean_save"
    final_delivery = "final_delivery"


DepthPreset = Literal[
    "Quick scan",
    "Standard brief",
    "Deep research",
    "Technical deep dive",
    "Custom",
]


class ResearchIntake(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    niche_research_topic: str = Field(alias="nicheResearchTopic", min_length=1)
    why_i_care: str = Field(alias="whyICare", min_length=1)
    intended_use: str = Field(alias="intendedUse", min_length=1)
    depth: DepthPreset
    custom_depth: str | None = Field(default=None, alias="customDepth")
    current_skill_level: str | None = Field(default=None, alias="currentSkillLevel")
    deadline: str | None = None
    output_type: str | None = Field(default=None, alias="outputType")

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def require_custom_depth_when_custom(self) -> "ResearchIntake":
        if self.depth == "Custom" and not self.custom_depth:
            raise ValueError("customDepth is required when depth is Custom")
        return self


class ResearchRunCreate(BaseModel):
    intake: ResearchIntake


class WorkflowStep(BaseModel):
    key: WorkflowPhase
    label: str
    status: Literal["pending", "active", "done", "blocked", "failed"]


class SourceRecord(BaseModel):
    id: str
    title: str
    url: str | None = None
    published_date: str | None = Field(default=None, alias="publishedDate")
    confidence: Literal["high", "medium", "low"]
    notes: str | None = None


class ApprovalRequest(BaseModel):
    id: str
    title: str
    body: str
    status: Literal["pending", "approved", "declined"] = "pending"


class SavedLocations(BaseModel):
    notion_prompt_url: str | None = Field(default=None, alias="notionPromptUrl")
    notion_response_url: str | None = Field(default=None, alias="notionResponseUrl")
    spaces_summary_key: str | None = Field(default=None, alias="spacesSummaryKey")


class RunProgress(BaseModel):
    timeline: list[WorkflowStep]
    source_records: list[SourceRecord] = Field(default_factory=list, alias="sourceRecords")
    tool_summaries: list[str] = Field(default_factory=list, alias="toolSummaries")
    decision_log: list[str] = Field(default_factory=list, alias="decisionLog")
    approval_requests: list[ApprovalRequest] = Field(default_factory=list, alias="approvalRequests")
    saved_locations: SavedLocations = Field(default_factory=SavedLocations, alias="savedLocations")


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


class ActionResponse(BaseModel):
    run_id: str = Field(alias="runId")
    status: RunStatus
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
        WorkflowPhase.prior_knowledge_retrieval: "Prior knowledge retrieval",
        WorkflowPhase.source_discovery: "Source discovery",
        WorkflowPhase.source_review: "Source review",
        WorkflowPhase.synthesis: "Synthesis",
        WorkflowPhase.notion_save: "Notion save",
        WorkflowPhase.digitalocean_save: "DigitalOcean save",
        WorkflowPhase.final_delivery: "Final delivery",
    }
    return RunProgress(
        timeline=[
            WorkflowStep(key=phase, label=label, status="pending") for phase, label in labels.items()
        ]
    )
