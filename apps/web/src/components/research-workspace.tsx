"use client";

import {
  depthPresets,
  requiredFields,
  type DepthPreset,
  type ResearchIntake,
  type RunRecord,
} from "@ai-research-agent/shared";
import {
  Ban,
  CircleCheck,
  ClipboardList,
  ExternalLink,
  Play,
  RefreshCw,
  RotateCcw,
  Send,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { StatusPill } from "./status-pill";

const emptyIntake: ResearchIntake = {
  nicheResearchTopic: "",
  whyICare: "",
  intendedUse: "",
  depth: "Standard brief",
  customDepth: "",
  currentSkillLevel: "",
  preferredFormat: "",
  trustedSources: "",
  excludedSources: "",
  deadline: "",
  outputType: "report",
  rawPrompt: "",
};

const terminalStatuses = new Set(["completed", "failed", "canceled"]);

export function ResearchWorkspace() {
  const [intake, setIntake] = useState<ResearchIntake>(emptyIntake);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  const missingFields = useMemo(() => {
    return requiredFields.filter((field) => !String(intake[field.key] ?? "").trim());
  }, [intake]);

  const isValid = missingFields.length === 0 && (intake.depth !== "Custom" || !!intake.customDepth?.trim());

  useEffect(() => {
    if (!activeRunId) return;

    let canceled = false;
    async function loadRun() {
      try {
        const response = await fetch(`/api/research/${activeRunId}`, { cache: "no-store" });
        if (!response.ok) throw new Error(await response.text());
        const nextRun = (await response.json()) as RunRecord;
        if (!canceled) setRun(nextRun);
      } catch (err) {
        if (!canceled) setError(err instanceof Error ? err.message : "Could not load run.");
      }
    }

    loadRun();
    const interval = window.setInterval(() => {
      if (!run || !terminalStatuses.has(run.status)) {
        loadRun();
      }
    }, 4000);

    return () => {
      canceled = true;
      window.clearInterval(interval);
    };
  }, [activeRunId, run?.status]);

  function updateField<K extends keyof ResearchIntake>(key: K, value: ResearchIntake[K]) {
    setIntake((current) => ({ ...current, [key]: value }));
  }

  function extractPromptFields() {
    const raw = intake.rawPrompt ?? "";
    const extract = (label: string) => {
      const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const pattern = new RegExp(`${escaped}\\s*:\\s*(.+?)(?=\\n[A-Z][^\\n:]{2,80}:|$)`, "is");
      return raw.match(pattern)?.[1]?.trim();
    };

    setIntake((current) => ({
      ...current,
      nicheResearchTopic: extract("Niche Research topic") ?? current.nicheResearchTopic,
      whyICare: extract("Why I care") ?? current.whyICare,
      intendedUse: extract("I want to use this for") ?? current.intendedUse,
      customDepth: extract("How deep/long should the research be") ?? current.customDepth,
      depth: extract("How deep/long should the research be") ? "Custom" : current.depth,
    }));
  }

  async function submitRun() {
    if (!isValid) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(intake),
      });
      if (!response.ok) throw new Error(await response.text());
      const created = (await response.json()) as RunRecord;
      setRun(created);
      setActiveRunId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start research.");
    } finally {
      setBusy(false);
    }
  }

  async function sendAction(action: "cancel" | "retry" | "resume") {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/research/${run.id}/action`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (!response.ok) throw new Error(await response.text());
      const refreshed = await fetch(`/api/research/${run.id}`, { cache: "no-store" });
      setRun((await refreshed.json()) as RunRecord);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} run.`);
    } finally {
      setBusy(false);
    }
  }

  async function submitFeedback() {
    if (!run || !feedback.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/research/${run.id}/action`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: "feedback", comment: feedback }),
      });
      if (!response.ok) throw new Error(await response.text());
      setFeedback("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save feedback.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="app-bar">
          <div className="brand">
            <span className="eyebrow">Vercel control surface</span>
            <h1>AI Research Agent</h1>
          </div>
          <ClipboardList aria-hidden size={22} />
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Research Intake</h2>
          </div>
          <div className="panel-body">
            <div className="form">
              <Field label="Chat-style prompt">
                <textarea
                  value={intake.rawPrompt}
                  onChange={(event) => updateField("rawPrompt", event.target.value)}
                />
                <button className="button ghost" type="button" onClick={extractPromptFields}>
                  <RefreshCw size={16} aria-hidden />
                  Extract fields
                </button>
              </Field>

              <Field label="Niche Research topic">
                <input
                  value={intake.nicheResearchTopic}
                  onChange={(event) => updateField("nicheResearchTopic", event.target.value)}
                />
              </Field>

              <Field label="Why I care">
                <textarea
                  value={intake.whyICare}
                  onChange={(event) => updateField("whyICare", event.target.value)}
                />
              </Field>

              <Field label="I want to use this for">
                <textarea
                  value={intake.intendedUse}
                  onChange={(event) => updateField("intendedUse", event.target.value)}
                />
              </Field>

              <Field label="How deep/long should the research be">
                <select
                  value={intake.depth}
                  onChange={(event) => updateField("depth", event.target.value as DepthPreset)}
                >
                  {depthPresets.map((depth) => (
                    <option key={depth}>{depth}</option>
                  ))}
                </select>
              </Field>

              {intake.depth === "Custom" ? (
                <Field label="Custom depth">
                  <input
                    value={intake.customDepth}
                    onChange={(event) => updateField("customDepth", event.target.value)}
                  />
                </Field>
              ) : null}

              <Field label="My current skill level">
                <input
                  value={intake.currentSkillLevel}
                  onChange={(event) => updateField("currentSkillLevel", event.target.value)}
                />
              </Field>

              <Field label="Preferred format">
                <input
                  value={intake.preferredFormat}
                  onChange={(event) => updateField("preferredFormat", event.target.value)}
                />
              </Field>

              <Field label="Sources I trust or want included">
                <textarea
                  value={intake.trustedSources}
                  onChange={(event) => updateField("trustedSources", event.target.value)}
                />
              </Field>

              <Field label="Sources I want excluded">
                <textarea
                  value={intake.excludedSources}
                  onChange={(event) => updateField("excludedSources", event.target.value)}
                />
              </Field>

              <Field label="Deadline or urgency">
                <input
                  value={intake.deadline}
                  onChange={(event) => updateField("deadline", event.target.value)}
                />
              </Field>

              <Field label="Output type">
                <select
                  value={intake.outputType}
                  onChange={(event) => updateField("outputType", event.target.value)}
                >
                  {["notes", "report", "roadmap", "checklist", "code plan", "video list", "tool comparison", "decision memo"].map(
                    (type) => (
                      <option key={type}>{type}</option>
                    ),
                  )}
                </select>
              </Field>

              {!isValid ? (
                <div className="error">
                  Missing info needed before I research:
                  {missingFields.map((field) => (
                    <div key={field.key}>- {field.label}: missing</div>
                  ))}
                  {intake.depth === "Custom" && !intake.customDepth?.trim() ? (
                    <div>- Custom depth: missing</div>
                  ) : null}
                </div>
              ) : null}

              <button className="button primary" type="button" onClick={submitRun} disabled={!isValid || busy}>
                <Play size={16} aria-hidden />
                Start research
              </button>
            </div>
          </div>
        </div>
      </aside>

      <section className="workspace">
        <div className="app-bar">
          <div className="brand">
            <span className="eyebrow">DigitalOcean worker status</span>
            <h1>Run Dashboard</h1>
          </div>
          {run ? <StatusPill status={run.status} /> : null}
        </div>

        {error ? <div className="error">{error}</div> : null}

        {run ? (
          <>
            <div className="status-grid">
              <Metric label="Run ID" value={run.id} />
              <Metric label="Created" value={formatDate(run.createdAt)} />
              <Metric label="Updated" value={formatDate(run.updatedAt)} />
              <Metric label="Depth" value={run.requestedDepth} />
            </div>

            <div className="button-row" style={{ marginTop: 14 }}>
              <button className="button" type="button" onClick={() => sendAction("retry")} disabled={busy}>
                <RotateCcw size={16} aria-hidden />
                Retry
              </button>
              <button className="button" type="button" onClick={() => sendAction("resume")} disabled={busy}>
                <Send size={16} aria-hidden />
                Resume
              </button>
              <button className="button danger" type="button" onClick={() => sendAction("cancel")} disabled={busy}>
                <Ban size={16} aria-hidden />
                Cancel
              </button>
            </div>

            <div className="content-grid">
              <div className="panel">
                <div className="panel-header">
                  <h2>Progress Timeline</h2>
                </div>
                <div className="panel-body timeline">
                  {run.progress.timeline.map((step) => (
                    <div className="timeline-row" key={step.key}>
                      <span className={`dot ${step.status}`} />
                      <span>{step.label}</span>
                      <span className="badge">{step.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="panel-header">
                  <h2>Saved Locations</h2>
                </div>
                <div className="panel-body list">
                  <SavedLocation label="Notion prompt" value={run.progress.savedLocations.notionPromptUrl} />
                  <SavedLocation label="Notion response" value={run.progress.savedLocations.notionResponseUrl} />
                  <SavedLocation label="Spaces summary" value={run.progress.savedLocations.spacesSummaryKey} />
                </div>
              </div>
            </div>

            <div className="content-grid">
              <PanelList title="Sources" items={run.progress.sourceRecords.map((source) => source.title)} />
              <PanelList title="Tool Summaries" items={run.progress.toolSummaries} />
            </div>

            <div className="content-grid">
              <PanelList title="Decision Log" items={run.progress.decisionLog} />
              <PanelList
                title="Approval Requests"
                items={run.progress.approvalRequests.map((request) => `${request.title}: ${request.status}`)}
              />
            </div>

            <div className="panel" style={{ marginTop: 14 }}>
              <div className="panel-header">
                <h2>Final Research Response</h2>
              </div>
              <div className="panel-body">
                {run.resultMarkdown ? (
                  <div className="report">{run.resultMarkdown}</div>
                ) : (
                  <div className="empty">The worker has not delivered a final response yet.</div>
                )}
              </div>
            </div>

            <div className="panel" style={{ marginTop: 14 }}>
              <div className="panel-header">
                <h2>Feedback</h2>
              </div>
              <div className="panel-body">
                <div className="field">
                  <label htmlFor="feedback">Was this too basic, too advanced, or about right?</label>
                  <textarea
                    id="feedback"
                    value={feedback}
                    onChange={(event) => setFeedback(event.target.value)}
                  />
                </div>
                <button className="button" type="button" onClick={submitFeedback} disabled={!feedback.trim() || busy}>
                  <CircleCheck size={16} aria-hidden />
                  Save feedback
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="empty">Submit the required intake fields to create a research run.</div>
        )}
      </section>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PanelList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
      </div>
      <div className="panel-body list">
        {items.length ? (
          items.map((item, index) => (
            <div className="list-item" key={`${title}-${index}`}>
              {item}
            </div>
          ))
        ) : (
          <div className="empty">No records yet.</div>
        )}
      </div>
    </div>
  );
}

function SavedLocation({ label, value }: { label: string; value?: string }) {
  return (
    <div className="list-item">
      <strong>{label}</strong>
      {value ? (
        value.startsWith("http") ? (
          <a href={value} target="_blank" rel="noreferrer">
            Open <ExternalLink size={13} aria-hidden />
          </a>
        ) : (
          <span className="muted">{value}</span>
        )
      ) : (
        <span className="muted">Not available yet</span>
      )}
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}
