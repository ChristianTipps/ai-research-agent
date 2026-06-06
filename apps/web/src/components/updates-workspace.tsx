"use client";

import type {
  EvaluationCase,
  EvaluationResult,
  EvalsOverview,
  MemoryDocument,
  MemoryOverview,
  ProposedUpdate,
  ToolConfigRecord,
  UpdateApplicationRecord,
  UpdateEvidenceSummary,
  UpdatesOverview,
  WorkflowVersion,
} from "@ai-research-agent/shared";
import {
  CircleCheck,
  ClipboardList,
  Database,
  FileText,
  FlaskConical,
  RefreshCw,
  SearchCheck,
  ServerCog,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { ThemeToggle } from "./theme-toggle";

type AdminActivity = {
  status: "running" | "success" | "error";
  title: string;
  detail: string;
};

export function UpdatesWorkspace() {
  const [overview, setOverview] = useState<UpdatesOverview | null>(null);
  const [memory, setMemory] = useState<MemoryOverview | null>(null);
  const [evals, setEvals] = useState<EvalsOverview | null>(null);
  const [passcode, setPasscode] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [activity, setActivity] = useState<AdminActivity | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadAll() {
    setError(null);
    try {
      const [updatesResponse, memoryResponse, evalsResponse] = await Promise.all([
        fetch("/api/updates", { cache: "no-store" }),
        fetch("/api/memory", { cache: "no-store" }),
        fetch("/api/evals", { cache: "no-store" }),
      ]);
      if (!updatesResponse.ok) throw new Error(await updatesResponse.text());
      if (!memoryResponse.ok) throw new Error(await memoryResponse.text());
      if (!evalsResponse.ok) throw new Error(await evalsResponse.text());
      setOverview((await updatesResponse.json()) as UpdatesOverview);
      setMemory((await memoryResponse.json()) as MemoryOverview);
      setEvals((await evalsResponse.json()) as EvalsOverview);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load evolution dashboard.";
      setError(message);
      throw new Error(message);
    }
  }

  useEffect(() => {
    loadAll().catch(() => undefined);
  }, []);

  async function checkPasscode() {
    setBusy(true);
    setActiveAction("passcode");
    setError(null);
    setActivity({
      status: "running",
      title: "Checking admin passcode",
      detail: "Verifying the passcode with the worker without changing memory, updates, or eval records.",
    });
    try {
      const response = await fetch("/api/admin/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const checkResponse = (await response.json()) as { message?: string };
      setActivity({
        status: "success",
        title: "Admin passcode works",
        detail: checkResponse.message ?? "The worker accepted this admin passcode.",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not verify admin passcode.";
      setError(message);
      setActivity({
        status: "error",
        title: "Admin passcode check failed",
        detail: message,
      });
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  async function refreshDashboard() {
    setBusy(true);
    setActiveAction("refresh");
    setActivity({
      status: "running",
      title: "Refreshing dashboard",
      detail: "Loading proposed updates, memory documents, workflow versions, and eval evidence.",
    });
    try {
      await loadAll();
      setActivity({
        status: "success",
        title: "Dashboard refreshed",
        detail: "The latest memory, eval, and update records are now visible.",
      });
    } catch {
      setActivity({
        status: "error",
        title: "Refresh failed",
        detail: "The dashboard could not load the latest records.",
      });
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  async function runAction(updateId: string, action: "approve" | "decline") {
    setBusy(true);
    setActiveAction(`${action}:${updateId}`);
    setError(null);
    setActivity({
      status: "running",
      title: action === "approve" ? "Approving update" : "Declining update",
      detail: "Sending the admin action to the worker and waiting for the update record to refresh.",
    });
    try {
      const response = await fetch(`/api/updates/${updateId}/action`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action, passcode }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const actionResponse = (await response.json()) as { message?: string };
      await loadAll();
      setActivity({
        status: "success",
        title: action === "approve" ? "Approval completed" : "Decline completed",
        detail: actionResponse.message ?? "The proposed update record has been refreshed.",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : `Could not ${action} update.`;
      setError(err instanceof Error ? err.message : `Could not ${action} update.`);
      setActivity({
        status: "error",
        title: action === "approve" ? "Approval failed" : "Decline failed",
        detail: message,
      });
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  async function bootstrapOperatingMemory() {
    setBusy(true);
    setActiveAction("bootstrap");
    setError(null);
    setActivity({
      status: "running",
      title: "Bootstrapping memory",
      detail: "Syncing required instruction files, tool configs, workflow records, and eval cases in Spaces.",
    });
    try {
      const response = await fetch("/api/memory/bootstrap", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const nextMemory = (await response.json()) as MemoryOverview;
      setMemory(nextMemory);
      await loadAll();
      setActivity({
        status: "success",
        title: "Memory bootstrap completed",
        detail: `${nextMemory.documents.length} document(s), ${nextMemory.toolConfigs.length} tool config(s), and ${nextMemory.updateApplications.length} update application record(s) are available.`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not bootstrap memory.";
      setError(err instanceof Error ? err.message : "Could not bootstrap memory.");
      setActivity({
        status: "error",
        title: "Memory bootstrap failed",
        detail: message,
      });
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  async function runQualityEvals() {
    setBusy(true);
    setActiveAction("evals");
    setError(null);
    setActivity({
      status: "running",
      title: "Running evaluations",
      detail: "Executing the active quality checks and saving the latest eval evidence.",
    });
    try {
      const response = await fetch("/api/evals/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      const nextEvals = (await response.json()) as EvalsOverview;
      setEvals(nextEvals);
      await loadAll();
      setActivity({
        status: "success",
        title: "Evaluations completed",
        detail: `${nextEvals.results.length} eval result(s) are now available across ${nextEvals.cases.length} active case(s).`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not run evaluations.";
      setError(err instanceof Error ? err.message : "Could not run evaluations.");
      setActivity({
        status: "error",
        title: "Evaluations failed",
        detail: message,
      });
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  const updates = overview?.proposedUpdates ?? [];
  const versions = overview?.workflowVersions ?? [];
  const applications = overview?.updateApplications ?? memory?.updateApplications ?? [];
  const documents = memory?.documents ?? [];
  const toolConfigs = memory?.toolConfigs ?? [];
  const cases = evals?.cases ?? [];
  const results = evals?.results ?? [];
  const evidenceByUpdateId = new Map((overview?.evidenceSummaries ?? []).map((summary) => [summary.updateId, summary]));

  return (
    <main className="shell">
      <section className="workspace-frame updates-frame">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">
              <Database aria-hidden size={20} />
            </span>
            <div>
              <span className="eyebrow">Memory and evolution</span>
              <h1>Updates</h1>
            </div>
          </div>
          <div className="button-row">
            <ThemeToggle />
            <a className="button" href="/">
              <SearchCheck size={16} aria-hidden />
              Research
            </a>
            <button className="button" type="button" onClick={refreshDashboard} disabled={busy}>
              <RefreshCw className={activeAction === "refresh" ? "spin" : undefined} size={16} aria-hidden />
              {activeAction === "refresh" ? "Refreshing" : "Refresh"}
            </button>
            <button className="button" type="button" onClick={bootstrapOperatingMemory} disabled={busy}>
              <ServerCog className={activeAction === "bootstrap" ? "spin" : undefined} size={16} aria-hidden />
              {activeAction === "bootstrap" ? "Bootstrapping" : "Bootstrap memory"}
            </button>
            <button className="button" type="button" onClick={runQualityEvals} disabled={busy}>
              <FlaskConical className={activeAction === "evals" ? "spin" : undefined} size={16} aria-hidden />
              {activeAction === "evals" ? "Running evals" : "Run evals"}
            </button>
          </div>
        </header>

        {error ? <div className="error">{error}</div> : null}
        {activity ? <AdminActivityNotice activity={activity} /> : null}

        <section className="panel">
          <div className="panel-header split">
            <div>
              <span className="eyebrow">Approval gate</span>
              <h2>Admin Controls</h2>
            </div>
            <ShieldCheck aria-hidden size={18} />
          </div>
          <div className="panel-body admin-controls">
            <div className="field admin-field">
              <label>Admin passcode</label>
              <input
                type="password"
                value={passcode}
                onChange={(event) => setPasscode(event.target.value)}
                placeholder="Required for approve, decline, bootstrap, and eval runs"
              />
              <div className="button-row">
                <button className="button" type="button" onClick={checkPasscode} disabled={busy || !passcode.trim()}>
                  <ShieldCheck className={activeAction === "passcode" ? "spin" : undefined} size={16} aria-hidden />
                  {activeAction === "passcode" ? "Checking" : "Check passcode"}
                </button>
              </div>
            </div>
            <div className="memory-summary">
              <MetricTile label="Documents" value={String(documents.length)} />
              <MetricTile label="Tool configs" value={String(toolConfigs.length)} />
              <MetricTile label="Eval cases" value={String(cases.length)} />
              <MetricTile label="Eval results" value={String(results.length)} />
            </div>
          </div>
        </section>

        <div className="updates-grid">
          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Pending and approved</span>
                <h2>Proposed Updates</h2>
              </div>
              <ClipboardList aria-hidden size={18} />
            </div>
            <div className="panel-body list">
              {updates.length ? (
                updates.map((update) => (
                  <UpdateCard
                    key={update.id}
                    update={update}
                    evidence={evidenceByUpdateId.get(update.id)}
                    busy={busy}
                    activeAction={activeAction}
                    onApprove={() => runAction(update.id, "approve")}
                    onDecline={() => runAction(update.id, "decline")}
                  />
                ))
              ) : (
                <div className="empty">No proposed updates yet.</div>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Runtime memory</span>
                <h2>Workflow Versions</h2>
              </div>
              <Database aria-hidden size={18} />
            </div>
            <div className="panel-body list">
              {versions.length ? (
                versions.map((version) => <VersionCard key={version.id} version={version} />)
              ) : (
                <div className="empty">No workflow versions yet.</div>
              )}
            </div>
          </section>
        </div>

        <div className="content-grid">
          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Spaces memory</span>
                <h2>Operating Documents</h2>
              </div>
              <FileText aria-hidden size={18} />
            </div>
            <div className="panel-body list">
              {memory?.warnings?.length ? <PanelNotice items={memory.warnings} /> : null}
              {documents.length ? documents.map((document) => <MemoryCard key={document.key} document={document} />) : <div className="empty">No memory documents loaded.</div>}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Tool registry</span>
                <h2>Tool Configs</h2>
              </div>
              <ServerCog aria-hidden size={18} />
            </div>
            <div className="panel-body list">
              {toolConfigs.length ? toolConfigs.map((config) => <ToolConfigCard key={config.key} config={config} />) : <div className="empty">No tool configs loaded.</div>}
            </div>
          </section>
        </div>

        <div className="content-grid">
          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Quality checks</span>
                <h2>Evaluation Cases</h2>
              </div>
              <FlaskConical aria-hidden size={18} />
            </div>
            <div className="panel-body list">
              {cases.length ? cases.map((testCase) => <EvalCaseCard key={testCase.id} testCase={testCase} />) : <div className="empty">No evaluation cases loaded.</div>}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Evidence</span>
                <h2>Eval Results and Update Applications</h2>
              </div>
              <CircleCheck aria-hidden size={18} />
            </div>
            <div className="panel-body list">
              {results.length ? results.slice(0, 8).map((result) => <EvalResultCard key={result.id} result={result} />) : <div className="empty">No eval results yet.</div>}
              {applications.length ? applications.slice(0, 8).map((application) => <ApplicationCard key={application.id} application={application} />) : null}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function UpdateCard({
  update,
  evidence,
  busy,
  activeAction,
  onApprove,
  onDecline,
}: {
  update: ProposedUpdate;
  evidence?: UpdateEvidenceSummary;
  busy: boolean;
  activeAction: string | null;
  onApprove: () => void;
  onDecline: () => void;
}) {
  const isPending = update.status === "pending";
  const approving = activeAction === `approve:${update.id}`;
  const declining = activeAction === `decline:${update.id}`;

  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{update.title}</strong>
        <span className={`badge ${update.status}`}>{update.status}</span>
      </div>
      <div className="source-meta">
        <span>{formatLabel(update.category)}</span>
        <span>{new Date(update.updatedAt).toLocaleString()}</span>
      </div>
      <p>{update.body}</p>
      {evidence ? <UpdateEvidence evidence={evidence} /> : null}
      {!isPending ? (
        <div className="form-note compact">
          This update is already {update.status}. Approve and decline actions are only available for pending updates.
        </div>
      ) : null}
      <div className="button-row">
        <button className="button" type="button" onClick={onApprove} disabled={busy || !isPending}>
          <CircleCheck className={approving ? "spin" : undefined} size={16} aria-hidden />
          {approving ? "Approving" : "Approve"}
        </button>
        <button className="button danger" type="button" onClick={onDecline} disabled={busy || !isPending}>
          <XCircle className={declining ? "spin" : undefined} size={16} aria-hidden />
          {declining ? "Declining" : "Decline"}
        </button>
      </div>
    </article>
  );
}

function AdminActivityNotice({ activity }: { activity: AdminActivity }) {
  return (
    <div className={`action-notice ${activity.status}`} role={activity.status === "error" ? "alert" : "status"}>
      <div className="action-notice-heading">
        {activity.status === "running" ? <RefreshCw className="spin" size={16} aria-hidden /> : null}
        {activity.status === "success" ? <CircleCheck size={16} aria-hidden /> : null}
        {activity.status === "error" ? <XCircle size={16} aria-hidden /> : null}
        <strong>{activity.title}</strong>
      </div>
      <p>{activity.detail}</p>
    </div>
  );
}

function UpdateEvidence({ evidence }: { evidence: UpdateEvidenceSummary }) {
  return (
    <div className="evidence-panel">
      <div className="update-card-heading">
        <strong>Evidence</strong>
        <span className={`badge ${evidenceBadgeClass(evidence.status)}`}>{evidence.status}</span>
      </div>
      <p>{evidence.summary}</p>
      <div className="source-meta">
        <span>{evidence.evidenceRunIds.length} evidence run(s)</span>
        <span>{evidence.evalResultCount} eval result(s)</span>
        <span>{evidence.evaluatedRunIds.length} evaluated run(s)</span>
        {evidence.latestResultAt ? <span>{new Date(evidence.latestResultAt).toLocaleString()}</span> : null}
      </div>
      {evidence.evidenceRunIds.length ? (
        <div className="source-meta">
          {evidence.evidenceRunIds.slice(0, 4).map((runId) => (
            <span key={runId}>{runId}</span>
          ))}
          {evidence.evidenceRunIds.length > 4 ? <span>+{evidence.evidenceRunIds.length - 4} more</span> : null}
        </div>
      ) : null}
    </div>
  );
}

function VersionCard({ version }: { version: WorkflowVersion }) {
  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{version.version}</strong>
        <span className={`badge ${version.status}`}>{version.status}</span>
      </div>
      <p>{version.notes}</p>
      {version.sourcePolicy ? <p>{version.sourcePolicy}</p> : null}
    </article>
  );
}

function MemoryCard({ document }: { document: MemoryDocument }) {
  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{document.title}</strong>
        <span className={`badge ${document.status}`}>{document.status}</span>
      </div>
      <div className="source-meta">
        <span>{formatLabel(document.category)}</span>
        <span>{document.key}</span>
        <span>{document.version}</span>
      </div>
      <p>{document.summary}</p>
    </article>
  );
}

function ToolConfigCard({ config }: { config: ToolConfigRecord }) {
  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{config.name}</strong>
        <span className={`badge ${config.enabled ? "approved" : "declined"}`}>{config.enabled ? "enabled" : "off"}</span>
      </div>
      <div className="source-meta">
        <span>{config.key}</span>
        <span>{config.version}</span>
      </div>
      <p>{config.summary}</p>
    </article>
  );
}

function EvalCaseCard({ testCase }: { testCase: EvaluationCase }) {
  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{testCase.title}</strong>
        <span className={`badge ${testCase.active ? "approved" : "archived"}`}>{testCase.active ? "active" : "off"}</span>
      </div>
      <p>{testCase.prompt}</p>
      <div className="source-meta">
        {testCase.tags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
    </article>
  );
}

function EvalResultCard({ result }: { result: EvaluationResult }) {
  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{result.caseId}</strong>
        <span className={`badge ${result.status}`}>{result.status}</span>
      </div>
      <div className="source-meta">
        <span>{Math.round(result.score * 100)}%</span>
        {result.runId ? <span>{result.runId}</span> : null}
        {result.artifactKey ? <span>{result.artifactKey}</span> : null}
      </div>
      <p>{result.summary}</p>
    </article>
  );
}

function ApplicationCard({ application }: { application: UpdateApplicationRecord }) {
  return (
    <article className="list-item update-card">
      <div className="update-card-heading">
        <strong>{application.updateId}</strong>
        <span className={`badge ${application.status === "runtime_applied" ? "approved" : application.status === "declined" ? "declined" : "pending"}`}>
          {formatLabel(application.status)}
        </span>
      </div>
      <div className="source-meta">
        <span>{formatLabel(application.category)}</span>
        {application.memoryKey ? <span>{application.memoryKey}</span> : null}
      </div>
      <p>{application.summary}</p>
    </article>
  );
}

function PanelNotice({ items }: { items: string[] }) {
  return (
    <div className="form-note">
      {items.map((item) => (
        <div key={item}>{item}</div>
      ))}
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric compact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

async function readErrorMessage(response: Response) {
  const text = await response.text();
  if (!text) return `Request failed with ${response.status}.`;
  try {
    const payload = JSON.parse(text) as { detail?: unknown; error?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    if (typeof payload.error === "string") return payload.error;
  } catch {
    return text;
  }
  return text;
}

function evidenceBadgeClass(status: UpdateEvidenceSummary["status"]) {
  if (status === "pass") return "pass";
  if (status === "fail") return "fail";
  return status;
}
