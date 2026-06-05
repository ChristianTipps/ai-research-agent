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
  | "prior_knowledge_retrieval"
  | "source_discovery"
  | "source_review"
  | "synthesis"
  | "notion_save"
  | "digitalocean_save"
  | "final_delivery";

export interface ResearchIntake {
  nicheResearchTopic: string;
  whyICare: string;
  intendedUse: string;
  depth: DepthPreset;
  customDepth?: string;
  currentSkillLevel?: SkillLevel | "";
  deadline?: string;
  outputType?: string;
}

export interface WorkflowStep {
  key: WorkflowPhase;
  label: string;
  status: "pending" | "active" | "done" | "blocked" | "failed";
}

export interface SourceRecord {
  id: string;
  title: string;
  url?: string;
  publishedDate?: string;
  confidence: "high" | "medium" | "low";
  notes?: string;
}

export interface ApprovalRequest {
  id: string;
  title: string;
  body: string;
  status: "pending" | "approved" | "declined";
}

export interface RunProgress {
  timeline: WorkflowStep[];
  sourceRecords: SourceRecord[];
  toolSummaries: string[];
  decisionLog: string[];
  approvalRequests: ApprovalRequest[];
  savedLocations: {
    notionPromptUrl?: string;
    notionResponseUrl?: string;
    spacesSummaryKey?: string;
  };
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

export const requiredFields: Array<{
  key: keyof Pick<ResearchIntake, "nicheResearchTopic" | "whyICare" | "intendedUse" | "depth">;
  label: string;
}> = [
  { key: "nicheResearchTopic", label: "Research topic" },
  { key: "whyICare", label: "Why it matters" },
  { key: "intendedUse", label: "Intended use" },
  { key: "depth", label: "Research depth" },
];
