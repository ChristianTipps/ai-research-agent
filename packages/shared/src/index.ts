export const depthPresets = [
  "Quick scan",
  "Standard brief",
  "Deep research",
  "Technical deep dive",
  "Custom",
] as const;

export type DepthPreset = (typeof depthPresets)[number];

export const skillLevels = [
  "New to the topic",
  "Working knowledge",
  "Advanced builder",
  "Expert",
  "Mixed audience",
] as const;

export type SkillLevel = (typeof skillLevels)[number];

export type RunStatus =
  | "queued"
  | "running"
  | "waiting_for_approval"
  | "checkpoint_saved"
  | "completed"
  | "failed"
  | "canceled";

export type WorkflowPhase =
  | "intake_validation"
  | "intake_normalization"
  | "prior_knowledge_retrieval"
  | "source_strategy"
  | "source_discovery"
  | "source_review"
  | "synthesis"
  | "report_formatting"
  | "notion_save"
  | "digitalocean_save"
  | "self_audit"
  | "final_delivery";

export type SourceType =
  | "official"
  | "primary"
  | "documentation"
  | "research_paper"
  | "github"
  | "news"
  | "community"
  | "youtube"
  | "web";

export type TranscriptStatus =
  | "not_applicable"
  | "available"
  | "transcript_unavailable"
  | "not_attempted";

export type ArtifactKind =
  | "final_report"
  | "run_summary"
  | "source_artifact"
  | "youtube_transcript"
  | "trust_report"
  | "workflow_version"
  | "instruction_snapshot";

export type UpdateCategory =
  | "instructions"
  | "source_policy"
  | "workflow"
  | "notion_formatting"
  | "ui"
  | "user_preference"
  | "evaluation"
  | "code_backlog";

export type UpdateStatus = "pending" | "approved" | "declined";

export interface ResearchIntake {
  nicheResearchTopic: string;
  whyICare: string;
  intendedUse: string;
  depth: DepthPreset;
  customDepth?: string;
  currentSkillLevel?: SkillLevel | "";
  deadline?: string;
  researchBudgetMinutes?: number;
  outputType?: string;
}

export interface WorkflowStep {
  key: WorkflowPhase;
  label: string;
  status: "pending" | "active" | "done" | "blocked" | "failed";
  summary?: string;
}

export interface SourceStrategy {
  requestedSourceTypes: SourceType[];
  requiredSourceTypes: SourceType[];
  sourceTargets: string[];
  minSources: number;
  maxSources: number;
  includeYouTube: boolean;
  rationale: string;
}

export interface SourceRecord {
  id: string;
  title: string;
  url?: string;
  sourceType: SourceType;
  author?: string;
  channelName?: string;
  publishedDate?: string;
  confidence: "high" | "medium" | "low";
  confidenceReason?: string;
  relevance?: string;
  transcriptStatus: TranscriptStatus;
  artifactKey?: string;
  notes?: string;
}

export interface ArtifactRecord {
  id: string;
  kind: ArtifactKind;
  label: string;
  key: string;
  url?: string;
  contentType: string;
  notes?: string;
  createdAt: string;
}

export interface TrustReport {
  overallConfidence: "high" | "medium" | "low";
  summary: string;
  strengths: string[];
  limitations: string[];
  sourceMix: string[];
  recommendations: string[];
}

export interface ApprovalRequest {
  id: string;
  title: string;
  body: string;
  status: "pending" | "approved" | "declined";
}

export interface RunProgress {
  timeline: WorkflowStep[];
  phaseMessage: string;
  progressPercent: number;
  sourceStrategy?: SourceStrategy;
  sourceRecords: SourceRecord[];
  artifactRecords: ArtifactRecord[];
  trustReport?: TrustReport;
  toolSummaries: string[];
  decisionLog: string[];
  approvalRequests: ApprovalRequest[];
  savedLocations: {
    notionPromptUrl?: string;
    notionResponseUrl?: string;
    spacesSummaryKey?: string;
    finalReportKey?: string;
    trustReportKey?: string;
  };
  workflowVersion: string;
  proposedUpdateCount: number;
}

export interface RunRecord {
  id: string;
  status: RunStatus;
  phase: WorkflowPhase;
  requestedDepth: string;
  intake: ResearchIntake;
  progress: RunProgress;
  resultMarkdown?: string;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProposedUpdate {
  id: string;
  title: string;
  category: UpdateCategory;
  status: UpdateStatus;
  body: string;
  evidenceRunIds: string[];
  createdAt: string;
  updatedAt: string;
  approvedAt?: string;
  declinedAt?: string;
}

export interface WorkflowVersion {
  id: string;
  version: string;
  status: "active" | "archived" | "proposed";
  notes: string;
  instructionSummary?: string;
  sourcePolicy?: string;
  createdAt: string;
  approvedAt?: string;
}

export interface UpdatesOverview {
  proposedUpdates: ProposedUpdate[];
  workflowVersions: WorkflowVersion[];
}

export const researchBudgetDefaults: Record<DepthPreset, number> = {
  "Quick scan": 2,
  "Standard brief": 5,
  "Deep research": 10,
  "Technical deep dive": 15,
  Custom: 10,
};

export const requiredFields: Array<{
  key: keyof Pick<ResearchIntake, "nicheResearchTopic" | "whyICare" | "intendedUse" | "depth">;
  label: string;
}> = [
  { key: "nicheResearchTopic", label: "Research topic" },
  { key: "whyICare", label: "Why it matters" },
  { key: "intendedUse", label: "Intended use" },
  { key: "depth", label: "Research depth" },
];
