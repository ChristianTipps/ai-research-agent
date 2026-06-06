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
  ServerCog,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

export function UpdatesWorkspace() {
  const [overview, setOverview] = useState<UpdatesOverview | null>(null);
  const [memory, setMemory] = useState<MemoryOverview | null>(null);
  const [evals, setEvals] = useState<EvalsOverview | null>(null);
  const [passcode, setPasscode] = useState("");
  const [busy, setBusy] = useState(false);
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
      setError(err instanceof Error ? err.message : "Could not load evolution dashboard.");
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function runAction(updateId: string, action: "approve" | "decline") {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/updates/${updateId}/action`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action, passcode }),
      });
      if (!response.ok) throw new Error(await response.text());
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} update.`);
    } finally {
      setBusy(false);
    }
  }

  async function bootstrapOperatingMemory() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/memory/bootstrap", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (!response.ok) throw new Error(await response.text());
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not bootstrap memory.");
    } finally {
      setBusy(false);
    }
  }

  async function runQualityEvals() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/evals/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ passcode }),
      });
      if (!response.ok) throw new Error(await response.text());
      setEvals((await response.json()) as EvalsOverview);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run evaluations.");
    } finally {
      setBusy(false);
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
            <button className="button" type="button" onClick={loadAll} disabled={busy}>
              <RefreshCw size={16} aria-hidden />
              Refresh
            </button>
            <button className="button" type="button" onClick={bootstrapOperatingMemory} disabled={busy}>
              <ServerCog size={16} aria-hidden />
              Bootstrap memory
            </button>
            <button className="button" type="button" onClick={runQualityEvals} disabled={busy}>
              <FlaskConical size={16} aria-hidden />
              Run evals
            </button>
          </div>
        </header>

        {error ? <div className="error">{error}</div> : null}

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
  onApprove,
  onDecline,
}: {
  update: ProposedUpdate;
  evidence?: UpdateEvidenceSummary;
  busy: boolean;
  onApprove: () => void;
  onDecline: () => void;
}) {
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
      <div className="button-row">
        <button className="button" type="button" onClick={onApprove} disabled={busy || update.status !== "pending"}>
          <CircleCheck size={16} aria-hidden />
          Approve
        </button>
        <button className="button danger" type="button" onClick={onDecline} disabled={busy || update.status !== "pending"}>
          <XCircle size={16} aria-hidden />
          Decline
        </button>
      </div>
    </article>
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

function evidenceBadgeClass(status: UpdateEvidenceSummary["status"]) {
  if (status === "pass") return "pass";
  if (status === "fail") return "fail";
  return status;
}
