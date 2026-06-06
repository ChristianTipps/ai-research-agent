import type { EvalsOverview, MemoryDocument, MemoryOverview, ResearchIntake, RunRecord, UpdatesOverview } from "@ai-research-agent/shared";

const backendUrl = process.env.AGENT_BACKEND_URL ?? "http://127.0.0.1:8080";
const backendToken = process.env.AGENT_BACKEND_TOKEN;

export class BackendRequestError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "BackendRequestError";
    this.status = status;
    this.payload = payload;
  }
}

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
    const payload = parseErrorPayload(text);
    throw new BackendRequestError(
      errorMessageFromPayload(payload, response.status),
      response.status,
      payload,
    );
  }
  return (await response.json()) as T;
}

function parseErrorPayload(text: string) {
  if (!text) return { error: "Backend request failed." };
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { error: text };
  }
}

function errorMessageFromPayload(payload: unknown, status: number) {
  if (payload && typeof payload === "object") {
    const detail = "detail" in payload ? payload.detail : undefined;
    const error = "error" in payload ? payload.error : undefined;
    if (typeof detail === "string") return detail;
    if (typeof error === "string") return error;
  }
  return `Backend request failed with ${status}`;
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

export async function listUpdates(): Promise<UpdatesOverview> {
  const response = await fetch(`${backendUrl}/updates`, {
    headers: headers(),
    cache: "no-store",
  });
  return parseResponse<UpdatesOverview>(response);
}

export async function listMemory(): Promise<MemoryOverview> {
  const response = await fetch(`${backendUrl}/memory`, {
    headers: headers(),
    cache: "no-store",
  });
  return parseResponse<MemoryOverview>(response);
}

export async function getMemoryDocument(key: string): Promise<MemoryDocument> {
  const response = await fetch(`${backendUrl}/memory/${encodeURI(key)}`, {
    headers: headers(),
    cache: "no-store",
  });
  return parseResponse<MemoryDocument>(response);
}

export async function bootstrapMemory(passcode?: string): Promise<MemoryOverview> {
  const response = await fetch(`${backendUrl}/memory/bootstrap`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ passcode }),
    cache: "no-store",
  });
  return parseResponse<MemoryOverview>(response);
}

export async function listEvals(): Promise<EvalsOverview> {
  const response = await fetch(`${backendUrl}/evals`, {
    headers: headers(),
    cache: "no-store",
  });
  return parseResponse<EvalsOverview>(response);
}

export async function runEvals(payload: { runId?: string; passcode?: string }): Promise<EvalsOverview> {
  const response = await fetch(`${backendUrl}/evals/run`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  return parseResponse<EvalsOverview>(response);
}

export async function runUpdateAction(updateId: string, action: "approve" | "decline", passcode?: string) {
  const response = await fetch(`${backendUrl}/updates/${updateId}/${action}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ passcode }),
    cache: "no-store",
  });
  return parseResponse<{ status: string; message: string }>(response);
}
