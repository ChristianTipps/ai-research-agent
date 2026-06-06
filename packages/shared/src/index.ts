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
  | "instruction_snapshot"
  | "memory_document"
  | "tool_config"
  | "evaluation_case"
  | "evaluation_result"
  | "update_application";

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

export type MemoryCategory =
  | "instructions"
  | "source_policy"
  | "notion_formatting"
  | "learning_output"
  | "tool_config"
  | "workflow"
  | "evaluation"
  | "approved_update"
  | "backlog";

export type EvaluationStatus = "pass" | "fail" | "warning";
export type EvidenceSummaryStatus = EvaluationStatus | "missing";

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
  youtubeUrls?: string[];
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

export interface MemoryDocument {
  key: string;
  title: string;
  category: MemoryCategory;
  contentType: string;
  version: string;
  status: "active" | "default" | "approved" | "missing";
  summary: string;
  content?: string;
  updatedAt?: string;
}

export interface ToolConfigRecord {
  key: string;
  name: string;
  enabled: boolean;
  summary: string;
  config: Record<string, unknown>;
  version: string;
}

export interface WorkflowVersionArtifact {
  key: string;
  version: string;
  status: "active" | "archived" | "proposed";
  summary: string;
  phases: string[];
  artifactPolicy: string[];
  approvalPolicy: string;
}

export interface MemoryContext {
  workflowVersion: string;
  instructionVersion: string;
  sourcePolicyVersion: string;
  notionFormattingVersion: string;
  learningOutputVersion: string;
  documents: MemoryDocument[];
  toolConfigs: ToolConfigRecord[];
  workflow?: WorkflowVersionArtifact;
  approvedUpdateCount: number;
  warnings: string[];
  loadedAt: string;
}

export interface EvaluationCase {
  id: string;
  title: string;
  prompt: string;
  expectedSignals: string[];
  forbiddenSignals: string[];
  tags: string[];
  active: boolean;
}

export interface EvaluationResult {
  id: string;
  caseId: string;
  status: EvaluationStatus;
  score: number;
  summary: string;
  runId?: string;
  evidence: string[];
  artifactKey?: string;
  createdAt: string;
}

export interface UpdateApplicationRecord {
  id: string;
  updateId: string;
  category: UpdateCategory;
  status: "runtime_applied" | "backlog_recorded" | "declined";
  summary: string;
  memoryKey?: string;
  artifactKey?: string;
  workflowVersion?: string;
  createdAt: string;
}

export interface MemoryOverview {
  documents: MemoryDocument[];
  toolConfigs: ToolConfigRecord[];
  workflow?: WorkflowVersionArtifact;
  updateApplications: UpdateApplicationRecord[];
  warnings: string[];
}

export interface EvalsOverview {
  cases: EvaluationCase[];
  results: EvaluationResult[];
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
  memoryContext?: MemoryContext;
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

export interface UpdateEvidenceSummary {
  updateId: string;
  evidenceRunIds: string[];
  evaluatedRunIds: string[];
  evalResultCount: number;
  passCount: number;
  warningCount: number;
  failCount: number;
  status: EvidenceSummaryStatus;
  summary: string;
  latestResultAt?: string;
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
  updateApplications: UpdateApplicationRecord[];
  evidenceSummaries: UpdateEvidenceSummary[];
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
