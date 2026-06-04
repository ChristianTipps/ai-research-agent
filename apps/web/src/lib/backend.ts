import type { ResearchIntake, RunRecord } from "@ai-research-agent/shared";

const backendUrl = process.env.AGENT_BACKEND_URL ?? "http://127.0.0.1:8080";
const backendToken = process.env.AGENT_BACKEND_TOKEN;

function headers() {
  const result: Record<string, string> = {
    "content-type": "application/json",
  };
  if (backendToken) {
    result.authorization = `Bearer ${backendToken}`;
  }
  return result;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Backend request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function createResearchRun(intake: ResearchIntake): Promise<RunRecord> {
  const response = await fetch(`${backendUrl}/runs`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ intake }),
    cache: "no-store",
  });
  return parseResponse<RunRecord>(response);
}

export async function getResearchRun(runId: string): Promise<RunRecord> {
  const response = await fetch(`${backendUrl}/runs/${runId}`, {
    headers: headers(),
    cache: "no-store",
  });
  return parseResponse<RunRecord>(response);
}

export async function runAction(runId: string, action: "cancel" | "retry" | "resume") {
  const response = await fetch(`${backendUrl}/runs/${runId}/${action}`, {
    method: "POST",
    headers: headers(),
    cache: "no-store",
  });
  return parseResponse<{ runId: string; status: string; message: string }>(response);
}

export async function saveFeedback(runId: string, payload: { rating?: string; comment?: string }) {
  const response = await fetch(`${backendUrl}/runs/${runId}/feedback`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  return parseResponse<{ runId: string; status: string; message: string }>(response);
}
