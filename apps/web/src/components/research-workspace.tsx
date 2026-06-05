"use client";

import {
  depthPresets,
  requiredFields,
  skillLevels,
  type DepthPreset,
  type ResearchIntake,
  type RunRecord,
  type SkillLevel,
} from "@ai-research-agent/shared";
import {
  Ban,
  CircleCheck,
  ClipboardList,
  ExternalLink,
  Layers3,
  Play,
  RotateCcw,
  Send,
} from "lucide-react";
import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import { StatusPill } from "./status-pill";

const outputTypes = [
  "report",
  "decision memo",
  "roadmap",
  "checklist",
  "code plan",
  "tool comparison",
  "notes",
] as const;

const emptyIntake: ResearchIntake = {
  nicheResearchTopic: "",
  whyICare: "",
  intendedUse: "",
  depth: "Standard brief",
  customDepth: "",
  currentSkillLevel: "Working knowledge",
  deadline: "",
  outputType: "report",
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
            <span className="eyebrow">Research console</span>
            <h1>AI Research Agent</h1>
          </div>
          <ClipboardList aria-hidden size={22} />
        </div>

        <div className="pattern-band" aria-hidden>
          <span className="shape shape-square" />
          <span className="shape shape-circle" />
          <span className="shape shape-diamond" />
          <span className="shape shape-line" />
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Research Intake</h2>
          </div>
          <div className="panel-body">
            <div className="form">
              <Field label="Research topic">
                <input
                  value={intake.nicheResearchTopic}
                  onChange={(event) => updateField("nicheResearchTopic", event.target.value)}
                />
              </Field>

              <Field label="Why it matters">
                <textarea
                  value={intake.whyICare}
                  onChange={(event) => updateField("whyICare", event.target.value)}
                />
              </Field>

              <Field label="Intended use">
                <textarea
                  value={intake.intendedUse}
                  onChange={(event) => updateField("intendedUse", event.target.value)}
                />
              </Field>

              <Field label="Research depth">
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

              <Field label="Skill level">
                <select
                  value={intake.currentSkillLevel}
                  onChange={(event) => updateField("currentSkillLevel", event.target.value as SkillLevel)}
                >
                  {skillLevels.map((level) => (
                    <option key={level}>{level}</option>
                  ))}
                </select>
              </Field>

              <Field label="Deadline or urgency">
                <input
                  value={intake.deadline}
                  onChange={(event) => updateField("deadline", event.target.value)}
                />
              </Field>

              <Field label="Output type">
                <select value={intake.outputType} onChange={(event) => updateField("outputType", event.target.value)}>
                  {outputTypes.map((type) => (
                    <option key={type}>{type}</option>
                  ))}
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
            <span className="eyebrow">Worker status</span>
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
                  <MarkdownReport markdown={run.resultMarkdown} />
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

function Field({ label, children }: { label: string; children: ReactNode }) {
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

function MarkdownReport({ markdown }: { markdown: string }) {
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (!listItems.length) return;
    const key = `list-${nodes.length}`;
    nodes.push(
      <ul key={key}>
        {listItems.map((item, index) => (
          <li key={`${key}-${index}`}>
            <InlineMarkdown text={item} />
          </li>
        ))}
      </ul>,
    );
    listItems = [];
  }

  markdown.split("\n").forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushList();
      const level = heading[1].length;
      const content = <InlineMarkdown text={heading[2]} />;
      if (level === 1) nodes.push(<h3 key={`h-${index}`}>{content}</h3>);
      else if (level === 2) nodes.push(<h4 key={`h-${index}`}>{content}</h4>);
      else nodes.push(<h5 key={`h-${index}`}>{content}</h5>);
      return;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      listItems.push(bullet[1]);
      return;
    }
    flushList();
    nodes.push(
      <p key={`p-${index}`}>
        <InlineMarkdown text={trimmed} />
      </p>,
    );
  });

  flushList();
  return (
    <article className="report">
      <Layers3 aria-hidden size={18} />
      <div>{nodes}</div>
    </article>
  );
}

function InlineMarkdown({ text }: { text: string }) {
  const pattern = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\[([^\]]+)\]\((https?:\/\/[^)]+)\))/g;
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text))) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2]) {
      parts.push(<strong key={`b-${match.index}`}>{match[2]}</strong>);
    } else if (match[4]) {
      parts.push(<code key={`c-${match.index}`}>{match[4]}</code>);
    } else if (match[6] && match[7]) {
      parts.push(
        <a key={`a-${match.index}`} href={match[7]} target="_blank" rel="noreferrer">
          {match[6]}
        </a>,
      );
    }
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return (
    <>
      {parts.map((part, index) => (
        <Fragment key={index}>{part}</Fragment>
      ))}
    </>
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
