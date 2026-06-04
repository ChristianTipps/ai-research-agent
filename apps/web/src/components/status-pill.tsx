import type { RunStatus } from "@ai-research-agent/shared";

export function StatusPill({ status }: { status: RunStatus | string }) {
  return <span className={`badge ${status}`}>{status.replaceAll("_", " ")}</span>;
}
