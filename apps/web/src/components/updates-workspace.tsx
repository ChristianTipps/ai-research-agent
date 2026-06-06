"use client";

import type { ProposedUpdate, UpdatesOverview, WorkflowVersion } from "@ai-research-agent/shared";
import { CircleCheck, Database, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

export function UpdatesWorkspace() {
  const [overview, setOverview] = useState<UpdatesOverview | null>(null);
  const [passcode, setPasscode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadUpdates() {
    setError(null);
    try {
      const response = await fetch("/api/updates", { cache: "no-store" });
      if (!response.ok) throw new Error(await response.text());
      setOverview((await response.json()) as UpdatesOverview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load updates.");
    }
  }

  useEffect(() => {
    loadUpdates();
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
      await loadUpdates();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action} update.`);
    } finally {
      setBusy(false);
    }
  }

  const updates = overview?.proposedUpdates ?? [];
  const versions = overview?.workflowVersions ?? [];

  return (
    <main className="shell">
      <section className="workspace-frame updates-frame">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">
              <Database aria-hidden size={20} />
            </span>
            <div>
              <span className="eyebrow">Version control</span>
              <h1>Updates</h1>
            </div>
          </div>
          <button className="button" type="button" onClick={loadUpdates} disabled={busy}>
            <RefreshCw size={16} aria-hidden />
            Refresh
          </button>
        </header>

        {error ? <div className="error">{error}</div> : null}

        <div className="updates-grid">
          <section className="panel">
            <div className="panel-header split">
              <div>
                <span className="eyebrow">Approval gate</span>
                <h2>Proposed Updates</h2>
              </div>
              <ShieldCheck aria-hidden size={18} />
            </div>
            <div className="panel-body">
              <div className="field admin-field">
                <label>Admin passcode</label>
                <input
                  type="password"
                  value={passcode}
                  onChange={(event) => setPasscode(event.target.value)}
                  placeholder="Required for approve/decline"
                />
              </div>
              <div className="list">
                {updates.length ? (
                  updates.map((update) => (
                    <UpdateCard
                      key={update.id}
                      update={update}
                      busy={busy}
                      onApprove={() => runAction(update.id, "approve")}
                      onDecline={() => runAction(update.id, "decline")}
                    />
                  ))
                ) : (
                  <div className="empty">No proposed updates yet.</div>
                )}
              </div>
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
      </section>
    </main>
  );
}

function UpdateCard({
  update,
  busy,
  onApprove,
  onDecline,
}: {
  update: ProposedUpdate;
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
        <span>{update.category.replaceAll("_", " ")}</span>
        <span>{new Date(update.updatedAt).toLocaleString()}</span>
      </div>
      <p>{update.body}</p>
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
