"use client";

import {
  depthPresets,
  researchBudgetDefaults,
  requiredFields,
  skillLevels,
  type DepthPreset,
  type ResearchIntake,
  type RunRecord,
  type SkillLevel,
  type SourceRecord,
} from "@ai-research-agent/shared";
import {
  Activity,
  Ban,
  BookOpen,
  CircleCheck,
  ClipboardList,
  Database,
  ExternalLink,
  FileText,
  Layers3,
  Play,
  RotateCcw,
  SearchCheck,
  Send,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";
import { StatusPill } from "./status-pill";

const emptyIntake: ResearchIntake = {
  nicheResearchTopic: "",
  whyICare: "",
  intendedUse: "",
  depth: "Standard brief",
  customDepth: "",
  currentSkillLevel: "Working knowledge",
  deadline: "",
  researchBudgetMinutes: researchBudgetDefaults["Standard brief"],
  outputType: "report",
  youtubeUrls: [],
};

const terminalStatuses = new Set(["completed", "failed", "canceled"]);

export function ResearchWorkspace() {
  const [intake, setIntake] = useState<ResearchIntake>(emptyIntake);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [reportExpanded, setReportExpanded] = useState(false);
  const [youtubeUrlText, setYoutubeUrlText] = useState("");

  const missingFields = useMemo(() => {
    return requiredFields.filter((field) => !String(intake[field.key] ?? "").trim());
  }, [intake]);

  const customDepthMissing = intake.depth === "Custom" && !intake.customDepth?.trim();
  const missingLabels = [
    ...missingFields.map((field) => field.label),
    ...(customDepthMissing ? ["Custom depth"] : []),
  ];
  const isValid = missingLabels.length === 0;
  const completionTotal = requiredFields.length + (intake.depth === "Custom" ? 1 : 0);
  const completionDone = Math.max(0, completionTotal - missingLabels.length);
  const completionPercent = `${Math.round((completionDone / completionTotal) * 100)}%`;

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

  function updateDepth(depth: DepthPreset) {
    setIntake((current) => ({
      ...current,
      depth,
      researchBudgetMinutes: researchBudgetDefaults[depth],
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
        body: JSON.stringify({
          ...intake,
          researchBudgetMinutes: intake.researchBudgetMinutes ?? researchBudgetDefaults[intake.depth],
          youtubeUrls: parseYoutubeUrls(youtubeUrlText),
        }),
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
      <section className="workspace-frame">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">
              <SearchCheck aria-hidden size={20} />
            </span>
            <div>
              <span className="eyebrow">Research console</span>
              <h1>AI Research Agent</h1>
            </div>
          </div>
          <div className="topbar-status">
            <a className="button" href="/updates">
              Updates
            </a>
            <span className={`badge ${isValid ? "ready" : "idle"}`}>
              {isValid ? "ready" : `${completionDone}/${completionTotal}`}
            </span>
            {run ? <StatusPill status={run.status} /> : <span className="badge idle">idle</span>}
          </div>
        </header>

        <div className="main-grid">
          <aside className="sidebar">
            <div className="signal-band" aria-hidden>
              <span className="shape shape-square" />
              <span className="shape shape-circle" />
              <span className="shape shape-diamond" />
              <span className="shape shape-line" />
              <span className="shape shape-corner" />
            </div>

            <div className="panel intake-panel">
              <div className="panel-header split">
                <div>
                  <span className="eyebrow">Intake</span>
                  <h2>Research Brief</h2>
                </div>
                <ClipboardList aria-hidden size={18} />
              </div>
              <div className="panel-body">
                <div className="intake-meter" aria-hidden>
                  <span style={{ width: completionPercent }} />
                </div>

                <div className="form">
                  <Field label="Research topic">
                    <input
                      value={intake.nicheResearchTopic}
                      onChange={(event) => updateField("nicheResearchTopic", event.target.value)}
                      placeholder="AI agents for small-business operations"
                    />
                  </Field>

                  <Field label="Why it matters">
                    <textarea
                      value={intake.whyICare}
                      onChange={(event) => updateField("whyICare", event.target.value)}
                      placeholder="What decision, project, or question this should support"
                    />
                  </Field>

                  <Field label="Intended use">
                    <textarea
                      value={intake.intendedUse}
                      onChange={(event) => updateField("intendedUse", event.target.value)}
                      placeholder="Briefing, build plan, comparison, learning path, or client notes"
                    />
                  </Field>

                  <Field label="YouTube URLs (optional)">
                    <textarea
                      value={youtubeUrlText}
                      onChange={(event) => setYoutubeUrlText(event.target.value)}
                      placeholder="Paste one video URL per line"
                    />
                  </Field>

                  <div className="field-row">
                    <Field label="Research depth">
                      <select
                        value={intake.depth}
                        onChange={(event) => updateDepth(event.target.value as DepthPreset)}
                      >
                        {depthPresets.map((depth) => (
                          <option key={depth}>{depth}</option>
                        ))}
                      </select>
                    </Field>

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
                  </div>

                  {intake.depth === "Custom" ? (
                    <Field label="Custom depth">
                      <input
                        value={intake.customDepth}
                        onChange={(event) => updateField("customDepth", event.target.value)}
                        placeholder="Source count, rigor, sections, or constraints"
                      />
                    </Field>
                  ) : null}

                  <div className="field-row">
                    <Field label="Deadline or urgency">
                      <input
                        value={intake.deadline}
                        onChange={(event) => updateField("deadline", event.target.value)}
                        placeholder="Today, this week, no rush"
                      />
                    </Field>

                    <Field label="Research budget">
                      <input
                        min={1}
                        max={60}
                        type="number"
                        value={intake.researchBudgetMinutes ?? researchBudgetDefaults[intake.depth]}
                        onChange={(event) =>
                          updateField("researchBudgetMinutes", Number(event.target.value) || researchBudgetDefaults[intake.depth])
                        }
                      />
                    </Field>
                  </div>

                  <div className={`form-note ${isValid ? "success" : ""}`}>
                    {isValid ? "Ready to start" : `Needs ${missingLabels.join(", ")}`}
                  </div>

                  <button
                    className="button primary full-width"
                    type="button"
                    onClick={submitRun}
                    disabled={!isValid || busy}
                  >
                    <Play size={16} aria-hidden />
                    Start research
                  </button>
                </div>
              </div>
            </div>
          </aside>

          <section className="workspace">
            <div className="dashboard-heading">
              <div>
                <span className="eyebrow">Worker status</span>
                <h2>{run?.intake.nicheResearchTopic || "Run Dashboard"}</h2>
              </div>
              {run ? (
                <div className="button-row">
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
              ) : null}
            </div>

            {error ? <div className="error">{error}</div> : null}

            {run ? (
              <>
                <div className="status-grid">
                  <Metric icon={<Activity size={16} aria-hidden />} label="Phase" value={formatLabel(run.phase)} />
                  <Metric icon={<FileText size={16} aria-hidden />} label="Depth" value={run.requestedDepth} />
                  <Metric icon={<SlidersHorizontal size={16} aria-hidden />} label="Budget" value={`${run.intake.researchBudgetMinutes ?? researchBudgetDefaults[run.intake.depth]} min`} />
                  <Metric icon={<Database size={16} aria-hidden />} label="Updated" value={formatDate(run.updatedAt)} />
                  <Metric icon={<ShieldCheck size={16} aria-hidden />} label="Run ID" value={run.id} />
                </div>

                <div className="content-grid">
                  <div className="panel">
                    <div className="panel-header split">
                      <h2>Progress Timeline</h2>
                      <StatusPill status={run.status} />
                    </div>
                    <div className="panel-body timeline">
                      <div className="phase-progress">
                        <div className="phase-progress-bar" aria-hidden>
                          <span style={{ width: `${run.progress.progressPercent}%` }} />
                        </div>
                        <p>{run.progress.phaseMessage}</p>
                      </div>
                      {run.progress.timeline.map((step) => (
                        <div className="timeline-row" key={step.key}>
                          <span className={`dot ${step.status}`} />
                          <span>{step.label}</span>
                          <span className={`badge ${step.status}`}>{formatLabel(step.status)}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="panel">
                    <div className="panel-header split">
                      <h2>Saved Locations</h2>
                      <Database aria-hidden size={18} />
                    </div>
                    <div className="panel-body saved-actions">
                      <SavedLocation label="Notion prompt" value={run.progress.savedLocations.notionPromptUrl} />
                      <SavedLocation label="Notion response" value={run.progress.savedLocations.notionResponseUrl} />
                      <SavedLocation label="Spaces summary" value={run.progress.savedLocations.spacesSummaryKey} />
                      <SavedLocation label="Final report" value={run.progress.savedLocations.finalReportKey} />
                      <SavedLocation label="Trust report" value={run.progress.savedLocations.trustReportKey} />
                    </div>
                  </div>
                </div>

                <div className="content-grid">
                  <SourcePanel sources={run.progress.sourceRecords} />
                  <PanelList title="Tool Summaries" items={run.progress.toolSummaries} />
                </div>

                <div className="content-grid">
                  <PanelList title="Decision Log" items={run.progress.decisionLog} />
                  <PanelList
                    title="Approval Requests"
                    items={run.progress.approvalRequests.map((request) => `${request.title}: ${request.status}`)}
                  />
                </div>

                <div className="panel section-gap">
                  <div className="panel-header split">
                    <h2>Final Research Response</h2>
                    <Layers3 aria-hidden size={18} />
                  </div>
                  <div className="panel-body">
                    {run.resultMarkdown ? (
                      <>
                        <div className="button-row report-actions">
                          <button className="button" type="button" onClick={() => setReportExpanded((value) => !value)}>
                            <BookOpen size={16} aria-hidden />
                            {reportExpanded ? "Preview" : "View full"}
                          </button>
                        </div>
                        <MarkdownReport markdown={reportExpanded ? run.resultMarkdown : previewMarkdown(run.resultMarkdown)} />
                      </>
                    ) : (
                      <div className="empty">No final response yet.</div>
                    )}
                  </div>
                </div>

                <div className="panel section-gap">
                  <div className="panel-header">
                    <h2>Feedback</h2>
                  </div>
                  <div className="panel-body feedback-grid">
                    <div className="field">
                      <label htmlFor="feedback">Feedback becomes a pending update note until you approve it.</label>
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
              <div className="empty-state">
                <ClipboardList aria-hidden size={26} />
                <h2>No active run</h2>
                <span className="muted">Intake required</span>
              </div>
            )}
          </section>
        </div>
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

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
    </div>
  );
}

function SourcePanel({ sources }: { sources: SourceRecord[] }) {
  const [expanded, setExpanded] = useState(false);
  const visibleSources = expanded ? sources : sources.slice(0, 4);
  const grouped = groupSources(visibleSources);

  return (
    <div className="panel">
      <div className="panel-header split">
        <h2>Sources</h2>
        <ShieldCheck aria-hidden size={18} />
      </div>
      <div className="panel-body list">
        {sources.length ? (
          <>
            {Object.entries(grouped).map(([sourceType, records]) => (
              <div className="source-group" key={sourceType}>
                <div className="source-group-title">
                  <span>{formatLabel(sourceType)}</span>
                  <span className="badge idle">{records.length}</span>
                </div>
                {records.map((source) => (
                  <div className="list-item source-item" key={source.id}>
                    <div>
                      <strong>{source.title}</strong>
                      <span className={`badge confidence-${source.confidence}`}>{source.confidence} confidence</span>
                    </div>
                    <div className="source-meta">
                      {source.channelName ? <span>{source.channelName}</span> : null}
                      {source.transcriptStatus !== "not_applicable" ? (
                        <span>{formatLabel(source.transcriptStatus)}</span>
                      ) : null}
                      {source.publishedDate ? <span>{source.publishedDate}</span> : null}
                    </div>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noreferrer">
                        Open <ExternalLink size={13} aria-hidden />
                      </a>
                    ) : null}
                    {source.confidenceReason ? <p>{source.confidenceReason}</p> : null}
                    {source.notes ? <p>{source.notes}</p> : null}
                  </div>
                ))}
              </div>
            ))}
            {sources.length > 4 ? (
              <button className="button" type="button" onClick={() => setExpanded((value) => !value)}>
                {expanded ? "Show fewer" : `View all ${sources.length}`}
              </button>
            ) : null}
          </>
        ) : (
          <div className="empty">No records yet.</div>
        )}
      </div>
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
    <div className="saved-location-button">
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

function groupSources(sources: SourceRecord[]) {
  return sources.reduce<Record<string, SourceRecord[]>>((groups, source) => {
    const key = source.sourceType || "web";
    groups[key] = groups[key] ? [...groups[key], source] : [source];
    return groups;
  }, {});
}

function previewMarkdown(markdown: string) {
  if (markdown.length <= 2600) return markdown;
  const preview = markdown.slice(0, 2600);
  const lastBreak = preview.lastIndexOf("\n\n");
  return `${preview.slice(0, lastBreak > 1200 ? lastBreak : preview.length)}\n\n_View full report to continue._`;
}

function parseYoutubeUrls(value: string) {
  const matches =
    value.match(/https?:\/\/[^\s,]+|www\.youtube\.com\/[^\s,]+|youtube\.com\/[^\s,]+|youtu\.be\/[^\s,]+/gi) ??
    value.split(/[\s,]+/);
  const urls = matches
    .map((item) => cleanYoutubeUrl(item))
    .filter((item): item is string => Boolean(item));
  return Array.from(new Set(urls.map((url) => url.toLowerCase())))
    .map((lowercaseUrl) => urls.find((url) => url.toLowerCase() === lowercaseUrl) ?? lowercaseUrl)
    .slice(0, 12);
}

function cleanYoutubeUrl(value: string) {
  let candidate = value.trim().replace(/^[()[\]{}<>.,;"']+|[()[\]{}<>.,;"']+$/g, "");
  if (!candidate) return null;
  if (candidate.startsWith("www.")) {
    candidate = `https://${candidate}`;
  } else if (candidate.startsWith("youtube.com/") || candidate.startsWith("youtu.be/")) {
    candidate = `https://${candidate}`;
  }
  try {
    const url = new URL(candidate);
    if (!["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"].includes(url.hostname.toLowerCase())) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

function MarkdownReport({ markdown }: { markdown: string }) {
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" = "ul";
  let codeLines: string[] = [];
  let codeLang = "";

  function flushList() {
    if (!listItems.length) return;
    const key = `list-${nodes.length}`;
    const children = listItems.map((item, index) => (
      <li key={`${key}-${index}`}>
        <InlineMarkdown text={item} />
      </li>
    ));
    nodes.push(listType === "ol" ? <ol key={key}>{children}</ol> : <ul key={key}>{children}</ul>);
    listItems = [];
  }

  function flushCode() {
    if (!codeLang && !codeLines.length) return;
    nodes.push(
      <pre key={`code-${nodes.length}`}>
        <code data-language={codeLang}>{codeLines.join("\n")}</code>
      </pre>,
    );
    codeLines = [];
    codeLang = "";
  }

  markdown.split("\n").forEach((line, index) => {
    const trimmed = line.trim();
    const fence = trimmed.match(/^```(\w+)?/);
    if (fence) {
      if (codeLang) {
        flushCode();
      } else {
        flushList();
        codeLang = fence[1] ?? "text";
      }
      return;
    }
    if (codeLang) {
      codeLines.push(line);
      return;
    }
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
      if (listType !== "ul") flushList();
      listType = "ul";
      listItems.push(bullet[1]);
      return;
    }
    const numbered = trimmed.match(/^\d+\.\s+(.+)$/);
    if (numbered) {
      if (listType !== "ol") flushList();
      listType = "ol";
      listItems.push(numbered[1]);
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
  flushCode();
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

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}
