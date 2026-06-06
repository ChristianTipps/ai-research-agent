from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .schemas import (
    ArtifactRecord,
    EvaluationResult,
    FeedbackCreate,
    ProposedUpdate,
    ResearchIntake,
    RunProgress,
    RunRecord,
    RunStatus,
    SourceRecord,
    TrustReport,
    UpdateCategory,
    UpdateApplicationRecord,
    UpdateStatus,
    WorkflowPhase,
    WorkflowVersion,
    initial_progress,
)
from .source_strategy import resolve_research_budget_minutes


class RunRepository(Protocol):
    def create_run(self, intake: ResearchIntake) -> RunRecord: ...
    def list_runs(self) -> list[RunRecord]: ...
    def get_run(self, run_id: str) -> RunRecord | None: ...
    def update_run(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        phase: WorkflowPhase | None = None,
        progress: RunProgress | None = None,
        result_markdown: str | None = None,
        error: str | None = None,
    ) -> RunRecord: ...
    def append_event(self, run_id: str, event_type: str, summary: str, metadata: dict[str, Any] | None = None) -> None: ...
    def add_sources(self, run_id: str, sources: list[SourceRecord]) -> None: ...
    def add_artifacts(self, run_id: str, artifacts: list[ArtifactRecord]) -> None: ...
    def save_trust_report(self, run_id: str, trust_report: TrustReport) -> None: ...
    def save_locations(
        self,
        run_id: str,
        *,
        notion_prompt_url: str | None = None,
        notion_response_url: str | None = None,
        spaces_summary_key: str | None = None,
        final_report_key: str | None = None,
        trust_report_key: str | None = None,
    ) -> RunRecord: ...
    def save_feedback(self, run_id: str, feedback: FeedbackCreate) -> int: ...
    def create_proposed_update(
        self,
        *,
        title: str,
        category: UpdateCategory,
        body: str,
        evidence_run_ids: list[str],
    ) -> ProposedUpdate: ...
    def list_proposed_updates(self) -> list[ProposedUpdate]: ...
    def set_proposed_update_status(self, update_id: str, status: UpdateStatus) -> ProposedUpdate: ...
    def create_workflow_version(
        self,
        *,
        version: str,
        notes: str,
        instruction_summary: str | None = None,
        source_policy: str | None = None,
    ) -> WorkflowVersion: ...
    def list_workflow_versions(self) -> list[WorkflowVersion]: ...
    def list_approved_runtime_updates(self) -> list[ProposedUpdate]: ...
    def create_update_application(
        self,
        *,
        update_id: str,
        category: UpdateCategory,
        status: str,
        summary: str,
        memory_key: str | None = None,
        artifact_key: str | None = None,
        workflow_version: str | None = None,
    ) -> UpdateApplicationRecord: ...
    def list_update_applications(self) -> list[UpdateApplicationRecord]: ...
    def save_evaluation_results(self, results: list[EvaluationResult]) -> None: ...
    def list_evaluation_results(self) -> list[EvaluationResult]: ...


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _loads(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    return datetime.fromisoformat(text)


class LocalSQLiteRunRepository:
    """Local development fallback. Production should use DigitalOcean PostgreSQL."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists research_runs (
                  id text primary key,
                  status text not null,
                  phase text not null,
                  requested_depth text not null,
                  intake text not null,
                  progress text not null,
                  result_markdown text,
                  notion_prompt_url text,
                  notion_response_url text,
                  spaces_summary_key text,
                  error text,
                  created_at text not null,
                  updated_at text not null
                );
                create table if not exists source_records (
                  id text primary key,
                  run_id text not null,
                  title text not null,
                  url text,
                  published_date text,
                  confidence text not null,
                  notes text,
                  created_at text not null
                );
                create table if not exists artifact_records (
                  id text primary key,
                  run_id text not null,
                  kind text not null,
                  label text not null,
                  key text not null,
                  url text,
                  content_type text not null,
                  notes text,
                  created_at text not null
                );
                create table if not exists trust_reports (
                  id text primary key,
                  run_id text not null,
                  report text not null,
                  created_at text not null
                );
                create table if not exists run_events (
                  id integer primary key autoincrement,
                  run_id text not null,
                  event_type text not null,
                  summary text not null,
                  metadata text not null,
                  created_at text not null
                );
                create table if not exists agent_feedback (
                  id integer primary key autoincrement,
                  run_id text not null,
                  rating text,
                  comment text,
                  created_at text not null
                );
                create table if not exists proposed_updates (
                  id text primary key,
                  title text not null,
                  category text not null,
                  status text not null,
                  body text not null,
                  evidence_run_ids text not null,
                  created_at text not null,
                  updated_at text not null,
                  approved_at text,
                  declined_at text
                );
                create table if not exists workflow_versions (
                  id text primary key,
                  version text not null,
                  status text not null,
                  notes text not null,
                  instruction_summary text,
                  source_policy text,
                  created_at text not null,
                  approved_at text
                );
                create table if not exists user_preferences (
                  id text primary key,
                  preference_key text not null,
                  preference_value text not null,
                  evidence_run_ids text not null,
                  status text not null,
                  created_at text not null,
                  updated_at text not null
                );
                create table if not exists update_applications (
                  id text primary key,
                  update_id text not null,
                  category text not null,
                  status text not null,
                  summary text not null,
                  memory_key text,
                  artifact_key text,
                  workflow_version text,
                  created_at text not null
                );
                create table if not exists evaluation_results (
                  id text primary key,
                  case_id text not null,
                  status text not null,
                  score real not null,
                  summary text not null,
                  run_id text,
                  evidence text not null,
                  artifact_key text,
                  created_at text not null
                );
                """
            )
            self._ensure_sqlite_columns(conn)
            self._ensure_default_workflow_version(conn)

    def _ensure_sqlite_columns(self, conn: sqlite3.Connection) -> None:
        existing = {row["name"] for row in conn.execute("pragma table_info(source_records)")}
        additions = {
            "source_type": "text not null default 'web'",
            "author": "text",
            "channel_name": "text",
            "confidence_reason": "text",
            "relevance": "text",
            "transcript_status": "text not null default 'not_applicable'",
            "artifact_key": "text",
        }
        for column, definition in additions.items():
            if column not in existing:
                conn.execute(f"alter table source_records add column {column} {definition}")
        existing_runs = {row["name"] for row in conn.execute("pragma table_info(research_runs)")}
        for column in ("final_report_key", "trust_report_key"):
            if column not in existing_runs:
                conn.execute(f"alter table research_runs add column {column} text")

    def _ensure_default_workflow_version(self, conn: sqlite3.Connection) -> None:
        existing = conn.execute("select id from workflow_versions limit 1").fetchone()
        if existing:
            return
        now = _iso_now()
        conn.execute(
            """
            insert into workflow_versions (
              id, version, status, notes, instruction_summary, source_policy, created_at, approved_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wf_research_v1",
                "research-workflow-v1",
                "active",
                "Initial staged research workflow with authorized update tracking.",
                "Use topic-aware source strategy, staged synthesis, and concise saved reasoning summaries.",
                "Prefer primary/current sources; label creator/community sources as perspective.",
                now,
                now,
            ),
        )

    def create_run(self, intake: ResearchIntake) -> RunRecord:
        run_id = _new_run_id()
        if intake.research_budget_minutes is None:
            intake.research_budget_minutes = resolve_research_budget_minutes(intake)
        progress = initial_progress()
        created = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                insert into research_runs (
                  id, status, phase, requested_depth, intake, progress, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    RunStatus.queued.value,
                    WorkflowPhase.intake_validation.value,
                    intake.custom_depth or intake.depth,
                    intake.model_dump_json(by_alias=True),
                    progress.model_dump_json(by_alias=True),
                    created,
                    created,
                ),
            )
        self.append_event(run_id, "run_created", "Run created and queued for DigitalOcean worker.")
        return self.get_run(run_id)  # type: ignore[return-value]

    def list_runs(self) -> list[RunRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from research_runs order by created_at desc limit 50"
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from research_runs where id = ?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def update_run(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        phase: WorkflowPhase | None = None,
        progress: RunProgress | None = None,
        result_markdown: str | None = None,
        error: str | None = None,
    ) -> RunRecord:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        with self._connect() as conn:
            conn.execute(
                """
                update research_runs
                set status = ?, phase = ?, progress = ?, result_markdown = coalesce(?, result_markdown),
                    error = ?, updated_at = ?
                where id = ?
                """,
                (
                    (status or current.status).value,
                    (phase or current.phase).value,
                    (progress or current.progress).model_dump_json(by_alias=True),
                    result_markdown,
                    error,
                    _iso_now(),
                    run_id,
                ),
            )
        return self.get_run(run_id)  # type: ignore[return-value]

    def append_event(
        self,
        run_id: str,
        event_type: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into run_events (run_id, event_type, summary, metadata, created_at)
                values (?, ?, ?, ?, ?)
                """,
                (run_id, event_type, summary, json.dumps(metadata or {}), _iso_now()),
            )

    def add_sources(self, run_id: str, sources: list[SourceRecord]) -> None:
        with self._connect() as conn:
            for source in sources:
                conn.execute(
                    """
                    insert or replace into source_records (
                      id, run_id, title, url, source_type, author, channel_name, published_date,
                      confidence, confidence_reason, relevance, transcript_status, artifact_key,
                      notes, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _source_params(run_id, source, sqlite=True),
                )

    def add_artifacts(self, run_id: str, artifacts: list[ArtifactRecord]) -> None:
        with self._connect() as conn:
            for artifact in artifacts:
                conn.execute(
                    """
                    insert or replace into artifact_records (
                      id, run_id, kind, label, key, url, content_type, notes, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _artifact_params(run_id, artifact),
                )

    def save_trust_report(self, run_id: str, trust_report: TrustReport) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into trust_reports (id, run_id, report, created_at)
                values (?, ?, ?, ?)
                """,
                (
                    f"trust_{run_id}",
                    run_id,
                    trust_report.model_dump_json(by_alias=True),
                    _iso_now(),
                ),
            )

    def save_locations(
        self,
        run_id: str,
        *,
        notion_prompt_url: str | None = None,
        notion_response_url: str | None = None,
        spaces_summary_key: str | None = None,
        final_report_key: str | None = None,
        trust_report_key: str | None = None,
    ) -> RunRecord:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        existing = current.progress.saved_locations
        existing.notion_prompt_url = notion_prompt_url or existing.notion_prompt_url
        existing.notion_response_url = notion_response_url or existing.notion_response_url
        existing.spaces_summary_key = spaces_summary_key or existing.spaces_summary_key
        existing.final_report_key = final_report_key or existing.final_report_key
        existing.trust_report_key = trust_report_key or existing.trust_report_key
        with self._connect() as conn:
            conn.execute(
                """
                update research_runs
                set notion_prompt_url = coalesce(?, notion_prompt_url),
                    notion_response_url = coalesce(?, notion_response_url),
                    spaces_summary_key = coalesce(?, spaces_summary_key),
                    final_report_key = coalesce(?, final_report_key),
                    trust_report_key = coalesce(?, trust_report_key),
                    progress = ?,
                    updated_at = ?
                where id = ?
                """,
                (
                    notion_prompt_url,
                    notion_response_url,
                    spaces_summary_key,
                    final_report_key,
                    trust_report_key,
                    current.progress.model_dump_json(by_alias=True),
                    _iso_now(),
                    run_id,
                ),
            )
        return self.get_run(run_id)  # type: ignore[return-value]

    def save_feedback(self, run_id: str, feedback: FeedbackCreate) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                insert into agent_feedback (run_id, rating, comment, created_at)
                values (?, ?, ?, ?)
                """,
                (run_id, feedback.rating, feedback.comment, _iso_now()),
            )
            return int(cursor.lastrowid)

    def create_proposed_update(
        self,
        *,
        title: str,
        category: UpdateCategory,
        body: str,
        evidence_run_ids: list[str],
    ) -> ProposedUpdate:
        update_id = _new_id("upd")
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                insert into proposed_updates (
                  id, title, category, status, body, evidence_run_ids, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (update_id, title, category, "pending", body, json.dumps(evidence_run_ids), now, now),
            )
        return self._get_proposed_update(update_id)

    def list_proposed_updates(self) -> list[ProposedUpdate]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from proposed_updates order by created_at desc limit 100"
            ).fetchall()
        return [self._row_to_update(row) for row in rows]

    def set_proposed_update_status(self, update_id: str, status: UpdateStatus) -> ProposedUpdate:
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                update proposed_updates
                set status = ?,
                    updated_at = ?,
                    approved_at = case when ? = 'approved' then ? else approved_at end,
                    declined_at = case when ? = 'declined' then ? else declined_at end
                where id = ?
                """,
                (status, now, status, now, status, now, update_id),
            )
        return self._get_proposed_update(update_id)

    def create_workflow_version(
        self,
        *,
        version: str,
        notes: str,
        instruction_summary: str | None = None,
        source_policy: str | None = None,
    ) -> WorkflowVersion:
        version_id = _new_id("wf")
        now = _iso_now()
        with self._connect() as conn:
            conn.execute("update workflow_versions set status = 'archived' where status = 'active'")
            conn.execute(
                """
                insert into workflow_versions (
                  id, version, status, notes, instruction_summary, source_policy, created_at, approved_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, version, "active", notes, instruction_summary, source_policy, now, now),
            )
        return self._get_workflow_version(version_id)

    def list_workflow_versions(self) -> list[WorkflowVersion]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from workflow_versions order by created_at desc limit 50"
            ).fetchall()
        return [self._row_to_workflow_version(row) for row in rows]

    def list_approved_runtime_updates(self) -> list[ProposedUpdate]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select * from proposed_updates
                where status = 'approved'
                  and category in ('instructions', 'source_policy', 'workflow', 'user_preference', 'evaluation')
                order by updated_at desc
                limit 20
                """
            ).fetchall()
        return [self._row_to_update(row) for row in rows]

    def create_update_application(
        self,
        *,
        update_id: str,
        category: UpdateCategory,
        status: str,
        summary: str,
        memory_key: str | None = None,
        artifact_key: str | None = None,
        workflow_version: str | None = None,
    ) -> UpdateApplicationRecord:
        application_id = _new_id("app")
        now = _iso_now()
        with self._connect() as conn:
            conn.execute(
                """
                insert into update_applications (
                  id, update_id, category, status, summary, memory_key, artifact_key, workflow_version, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (application_id, update_id, category, status, summary, memory_key, artifact_key, workflow_version, now),
            )
        return self._get_update_application(application_id)

    def list_update_applications(self) -> list[UpdateApplicationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from update_applications order by created_at desc limit 100"
            ).fetchall()
        return [self._row_to_update_application(row) for row in rows]

    def save_evaluation_results(self, results: list[EvaluationResult]) -> None:
        with self._connect() as conn:
            for result in results:
                conn.execute(
                    """
                    insert or replace into evaluation_results (
                      id, case_id, status, score, summary, run_id, evidence, artifact_key, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.id,
                        result.case_id,
                        result.status,
                        result.score,
                        result.summary,
                        result.run_id,
                        json.dumps(result.evidence),
                        result.artifact_key,
                        result.created_at.isoformat(),
                    ),
                )

    def list_evaluation_results(self) -> list[EvaluationResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from evaluation_results order by created_at desc limit 100"
            ).fetchall()
        return [self._row_to_evaluation_result(row) for row in rows]

    def _get_proposed_update(self, update_id: str) -> ProposedUpdate:
        with self._connect() as conn:
            row = conn.execute("select * from proposed_updates where id = ?", (update_id,)).fetchone()
        if row is None:
            raise KeyError(update_id)
        return self._row_to_update(row)

    def _get_workflow_version(self, version_id: str) -> WorkflowVersion:
        with self._connect() as conn:
            row = conn.execute("select * from workflow_versions where id = ?", (version_id,)).fetchone()
        if row is None:
            raise KeyError(version_id)
        return self._row_to_workflow_version(row)

    def _get_update_application(self, application_id: str) -> UpdateApplicationRecord:
        with self._connect() as conn:
            row = conn.execute("select * from update_applications where id = ?", (application_id,)).fetchone()
        if row is None:
            raise KeyError(application_id)
        return self._row_to_update_application(row)

    def _row_to_run(self, row: sqlite3.Row) -> RunRecord:
        data = dict(row)
        return RunRecord(
            id=data["id"],
            status=data["status"],
            phase=data["phase"],
            requestedDepth=data["requested_depth"],
            intake=json.loads(data["intake"]),
            progress=json.loads(data["progress"]),
            resultMarkdown=data["result_markdown"],
            error=data["error"],
            createdAt=_dt(data["created_at"]),
            updatedAt=_dt(data["updated_at"]),
        )

    def _row_to_update(self, row: sqlite3.Row) -> ProposedUpdate:
        data = dict(row)
        return ProposedUpdate(
            id=data["id"],
            title=data["title"],
            category=data["category"],
            status=data["status"],
            body=data["body"],
            evidenceRunIds=json.loads(data["evidence_run_ids"]),
            createdAt=_dt(data["created_at"]),
            updatedAt=_dt(data["updated_at"]),
            approvedAt=_dt(data["approved_at"]) if data["approved_at"] else None,
            declinedAt=_dt(data["declined_at"]) if data["declined_at"] else None,
        )

    def _row_to_workflow_version(self, row: sqlite3.Row) -> WorkflowVersion:
        data = dict(row)
        return WorkflowVersion(
            id=data["id"],
            version=data["version"],
            status=data["status"],
            notes=data["notes"],
            instructionSummary=data["instruction_summary"],
            sourcePolicy=data["source_policy"],
            createdAt=_dt(data["created_at"]),
            approvedAt=_dt(data["approved_at"]) if data["approved_at"] else None,
        )

    def _row_to_update_application(self, row: sqlite3.Row) -> UpdateApplicationRecord:
        data = dict(row)
        return UpdateApplicationRecord(
            id=data["id"],
            updateId=data["update_id"],
            category=data["category"],
            status=data["status"],
            summary=data["summary"],
            memoryKey=data["memory_key"],
            artifactKey=data["artifact_key"],
            workflowVersion=data["workflow_version"],
            createdAt=_dt(data["created_at"]),
        )

    def _row_to_evaluation_result(self, row: sqlite3.Row) -> EvaluationResult:
        data = dict(row)
        return EvaluationResult(
            id=data["id"],
            caseId=data["case_id"],
            status=data["status"],
            score=float(data["score"]),
            summary=data["summary"],
            runId=data["run_id"],
            evidence=json.loads(data["evidence"]),
            artifactKey=data["artifact_key"],
            createdAt=_dt(data["created_at"]),
        )


class PostgresRunRepository:
    def __init__(self, database_url: str) -> None:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb

        self.database_url = database_url
        self.psycopg = psycopg
        self.dict_row = dict_row
        self.Jsonb = Jsonb
        self._init()

    def _connect(self):
        return self.psycopg.connect(self.database_url, row_factory=self.dict_row)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists research_runs (
                  id text primary key,
                  status text not null,
                  phase text not null,
                  requested_depth text not null,
                  intake jsonb not null,
                  progress jsonb not null default '{}'::jsonb,
                  result_markdown text,
                  notion_prompt_url text,
                  notion_response_url text,
                  spaces_summary_key text,
                  error text,
                  created_at timestamptz not null default now(),
                  updated_at timestamptz not null default now()
                );
                alter table research_runs add column if not exists final_report_key text;
                alter table research_runs add column if not exists trust_report_key text;
                create table if not exists source_records (
                  id text primary key,
                  run_id text not null references research_runs(id) on delete cascade,
                  title text not null,
                  url text,
                  published_date text,
                  confidence text not null,
                  notes text,
                  created_at timestamptz not null default now()
                );
                alter table source_records add column if not exists source_type text not null default 'web';
                alter table source_records add column if not exists author text;
                alter table source_records add column if not exists channel_name text;
                alter table source_records add column if not exists confidence_reason text;
                alter table source_records add column if not exists relevance text;
                alter table source_records add column if not exists transcript_status text not null default 'not_applicable';
                alter table source_records add column if not exists artifact_key text;
                create table if not exists artifact_records (
                  id text primary key,
                  run_id text not null references research_runs(id) on delete cascade,
                  kind text not null,
                  label text not null,
                  key text not null,
                  url text,
                  content_type text not null,
                  notes text,
                  created_at timestamptz not null default now()
                );
                create table if not exists trust_reports (
                  id text primary key,
                  run_id text not null references research_runs(id) on delete cascade,
                  report jsonb not null,
                  created_at timestamptz not null default now()
                );
                create table if not exists run_events (
                  id bigserial primary key,
                  run_id text not null references research_runs(id) on delete cascade,
                  event_type text not null,
                  summary text not null,
                  metadata jsonb not null default '{}'::jsonb,
                  created_at timestamptz not null default now()
                );
                create table if not exists agent_feedback (
                  id bigserial primary key,
                  run_id text not null references research_runs(id) on delete cascade,
                  rating text,
                  comment text,
                  created_at timestamptz not null default now()
                );
                create table if not exists proposed_updates (
                  id text primary key,
                  title text not null,
                  category text not null,
                  status text not null,
                  body text not null,
                  evidence_run_ids jsonb not null default '[]'::jsonb,
                  created_at timestamptz not null default now(),
                  updated_at timestamptz not null default now(),
                  approved_at timestamptz,
                  declined_at timestamptz
                );
                create table if not exists workflow_versions (
                  id text primary key,
                  version text not null,
                  status text not null,
                  notes text not null,
                  instruction_summary text,
                  source_policy text,
                  created_at timestamptz not null default now(),
                  approved_at timestamptz
                );
                create table if not exists user_preferences (
                  id text primary key,
                  preference_key text not null,
                  preference_value jsonb not null,
                  evidence_run_ids jsonb not null default '[]'::jsonb,
                  status text not null,
                  created_at timestamptz not null default now(),
                  updated_at timestamptz not null default now()
                );
                create table if not exists update_applications (
                  id text primary key,
                  update_id text not null,
                  category text not null,
                  status text not null,
                  summary text not null,
                  memory_key text,
                  artifact_key text,
                  workflow_version text,
                  created_at timestamptz not null default now()
                );
                create table if not exists evaluation_results (
                  id text primary key,
                  case_id text not null,
                  status text not null,
                  score double precision not null,
                  summary text not null,
                  run_id text,
                  evidence jsonb not null default '[]'::jsonb,
                  artifact_key text,
                  created_at timestamptz not null default now()
                );
                insert into workflow_versions (
                  id, version, status, notes, instruction_summary, source_policy, approved_at
                )
                select
                  'wf_research_v1',
                  'research-workflow-v1',
                  'active',
                  'Initial staged research workflow with authorized update tracking.',
                  'Use topic-aware source strategy, staged synthesis, and concise saved reasoning summaries.',
                  'Prefer primary/current sources; label creator/community sources as perspective.',
                  now()
                where not exists (select 1 from workflow_versions);
                """
            )

    def create_run(self, intake: ResearchIntake) -> RunRecord:
        run_id = _new_run_id()
        if intake.research_budget_minutes is None:
            intake.research_budget_minutes = resolve_research_budget_minutes(intake)
        progress = initial_progress()
        with self._connect() as conn:
            conn.execute(
                """
                insert into research_runs (
                  id, status, phase, requested_depth, intake, progress
                ) values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    RunStatus.queued.value,
                    WorkflowPhase.intake_validation.value,
                    intake.custom_depth or intake.depth,
                    self.Jsonb(intake.model_dump(by_alias=True, mode="json")),
                    self.Jsonb(progress.model_dump(by_alias=True, mode="json")),
                ),
            )
        self.append_event(run_id, "run_created", "Run created and queued for DigitalOcean worker.")
        return self.get_run(run_id)  # type: ignore[return-value]

    def list_runs(self) -> list[RunRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from research_runs order by created_at desc limit 50"
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from research_runs where id = %s", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def update_run(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        phase: WorkflowPhase | None = None,
        progress: RunProgress | None = None,
        result_markdown: str | None = None,
        error: str | None = None,
    ) -> RunRecord:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        with self._connect() as conn:
            conn.execute(
                """
                update research_runs
                set status = %s, phase = %s, progress = %s,
                    result_markdown = coalesce(%s, result_markdown),
                    error = %s,
                    updated_at = now()
                where id = %s
                """,
                (
                    (status or current.status).value,
                    (phase or current.phase).value,
                    self.Jsonb((progress or current.progress).model_dump(by_alias=True, mode="json")),
                    result_markdown,
                    error,
                    run_id,
                ),
            )
        return self.get_run(run_id)  # type: ignore[return-value]

    def append_event(
        self,
        run_id: str,
        event_type: str,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into run_events (run_id, event_type, summary, metadata)
                values (%s, %s, %s, %s)
                """,
                (run_id, event_type, summary, self.Jsonb(metadata or {})),
            )

    def add_sources(self, run_id: str, sources: list[SourceRecord]) -> None:
        with self._connect() as conn:
            for source in sources:
                conn.execute(
                    """
                    insert into source_records (
                      id, run_id, title, url, source_type, author, channel_name, published_date,
                      confidence, confidence_reason, relevance, transcript_status, artifact_key, notes
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      title = excluded.title,
                      url = excluded.url,
                      source_type = excluded.source_type,
                      author = excluded.author,
                      channel_name = excluded.channel_name,
                      published_date = excluded.published_date,
                      confidence = excluded.confidence,
                      confidence_reason = excluded.confidence_reason,
                      relevance = excluded.relevance,
                      transcript_status = excluded.transcript_status,
                      artifact_key = excluded.artifact_key,
                      notes = excluded.notes
                    """,
                    _source_params(run_id, source, sqlite=False),
                )

    def add_artifacts(self, run_id: str, artifacts: list[ArtifactRecord]) -> None:
        with self._connect() as conn:
            for artifact in artifacts:
                conn.execute(
                    """
                    insert into artifact_records (
                      id, run_id, kind, label, key, url, content_type, notes, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      kind = excluded.kind,
                      label = excluded.label,
                      key = excluded.key,
                      url = excluded.url,
                      content_type = excluded.content_type,
                      notes = excluded.notes
                    """,
                    _artifact_params(run_id, artifact),
                )

    def save_trust_report(self, run_id: str, trust_report: TrustReport) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into trust_reports (id, run_id, report)
                values (%s, %s, %s)
                on conflict (id) do update set report = excluded.report
                """,
                (f"trust_{run_id}", run_id, self.Jsonb(trust_report.model_dump(by_alias=True, mode="json"))),
            )

    def save_locations(
        self,
        run_id: str,
        *,
        notion_prompt_url: str | None = None,
        notion_response_url: str | None = None,
        spaces_summary_key: str | None = None,
        final_report_key: str | None = None,
        trust_report_key: str | None = None,
    ) -> RunRecord:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        existing = current.progress.saved_locations
        existing.notion_prompt_url = notion_prompt_url or existing.notion_prompt_url
        existing.notion_response_url = notion_response_url or existing.notion_response_url
        existing.spaces_summary_key = spaces_summary_key or existing.spaces_summary_key
        existing.final_report_key = final_report_key or existing.final_report_key
        existing.trust_report_key = trust_report_key or existing.trust_report_key
        with self._connect() as conn:
            conn.execute(
                """
                update research_runs
                set notion_prompt_url = coalesce(%s, notion_prompt_url),
                    notion_response_url = coalesce(%s, notion_response_url),
                    spaces_summary_key = coalesce(%s, spaces_summary_key),
                    final_report_key = coalesce(%s, final_report_key),
                    trust_report_key = coalesce(%s, trust_report_key),
                    progress = %s,
                    updated_at = now()
                where id = %s
                """,
                (
                    notion_prompt_url,
                    notion_response_url,
                    spaces_summary_key,
                    final_report_key,
                    trust_report_key,
                    self.Jsonb(current.progress.model_dump(by_alias=True, mode="json")),
                    run_id,
                ),
            )
        return self.get_run(run_id)  # type: ignore[return-value]

    def save_feedback(self, run_id: str, feedback: FeedbackCreate) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into agent_feedback (run_id, rating, comment)
                values (%s, %s, %s)
                returning id
                """,
                (run_id, feedback.rating, feedback.comment),
            ).fetchone()
            return int(row["id"])

    def create_proposed_update(
        self,
        *,
        title: str,
        category: UpdateCategory,
        body: str,
        evidence_run_ids: list[str],
    ) -> ProposedUpdate:
        update_id = _new_id("upd")
        with self._connect() as conn:
            conn.execute(
                """
                insert into proposed_updates (
                  id, title, category, status, body, evidence_run_ids
                ) values (%s, %s, %s, %s, %s, %s)
                """,
                (update_id, title, category, "pending", body, self.Jsonb(evidence_run_ids)),
            )
        return self._get_proposed_update(update_id)

    def list_proposed_updates(self) -> list[ProposedUpdate]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from proposed_updates order by created_at desc limit 100"
            ).fetchall()
        return [self._row_to_update(row) for row in rows]

    def set_proposed_update_status(self, update_id: str, status: UpdateStatus) -> ProposedUpdate:
        with self._connect() as conn:
            conn.execute(
                """
                update proposed_updates
                set status = %s,
                    updated_at = now(),
                    approved_at = case when %s = 'approved' then now() else approved_at end,
                    declined_at = case when %s = 'declined' then now() else declined_at end
                where id = %s
                """,
                (status, status, status, update_id),
            )
        return self._get_proposed_update(update_id)

    def create_workflow_version(
        self,
        *,
        version: str,
        notes: str,
        instruction_summary: str | None = None,
        source_policy: str | None = None,
    ) -> WorkflowVersion:
        version_id = _new_id("wf")
        with self._connect() as conn:
            conn.execute("update workflow_versions set status = 'archived' where status = 'active'")
            conn.execute(
                """
                insert into workflow_versions (
                  id, version, status, notes, instruction_summary, source_policy, approved_at
                ) values (%s, %s, %s, %s, %s, %s, now())
                """,
                (version_id, version, "active", notes, instruction_summary, source_policy),
            )
        return self._get_workflow_version(version_id)

    def list_workflow_versions(self) -> list[WorkflowVersion]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from workflow_versions order by created_at desc limit 50"
            ).fetchall()
        return [self._row_to_workflow_version(row) for row in rows]

    def list_approved_runtime_updates(self) -> list[ProposedUpdate]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select * from proposed_updates
                where status = 'approved'
                  and category in ('instructions', 'source_policy', 'workflow', 'user_preference', 'evaluation')
                order by updated_at desc
                limit 20
                """
            ).fetchall()
        return [self._row_to_update(row) for row in rows]

    def create_update_application(
        self,
        *,
        update_id: str,
        category: UpdateCategory,
        status: str,
        summary: str,
        memory_key: str | None = None,
        artifact_key: str | None = None,
        workflow_version: str | None = None,
    ) -> UpdateApplicationRecord:
        application_id = _new_id("app")
        with self._connect() as conn:
            conn.execute(
                """
                insert into update_applications (
                  id, update_id, category, status, summary, memory_key, artifact_key, workflow_version
                ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (application_id, update_id, category, status, summary, memory_key, artifact_key, workflow_version),
            )
        return self._get_update_application(application_id)

    def list_update_applications(self) -> list[UpdateApplicationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from update_applications order by created_at desc limit 100"
            ).fetchall()
        return [self._row_to_update_application(row) for row in rows]

    def save_evaluation_results(self, results: list[EvaluationResult]) -> None:
        with self._connect() as conn:
            for result in results:
                conn.execute(
                    """
                    insert into evaluation_results (
                      id, case_id, status, score, summary, run_id, evidence, artifact_key, created_at
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      case_id = excluded.case_id,
                      status = excluded.status,
                      score = excluded.score,
                      summary = excluded.summary,
                      run_id = excluded.run_id,
                      evidence = excluded.evidence,
                      artifact_key = excluded.artifact_key
                    """,
                    (
                        result.id,
                        result.case_id,
                        result.status,
                        result.score,
                        result.summary,
                        result.run_id,
                        self.Jsonb(result.evidence),
                        result.artifact_key,
                        result.created_at,
                    ),
                )

    def list_evaluation_results(self) -> list[EvaluationResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from evaluation_results order by created_at desc limit 100"
            ).fetchall()
        return [self._row_to_evaluation_result(row) for row in rows]

    def _get_proposed_update(self, update_id: str) -> ProposedUpdate:
        with self._connect() as conn:
            row = conn.execute("select * from proposed_updates where id = %s", (update_id,)).fetchone()
        if row is None:
            raise KeyError(update_id)
        return self._row_to_update(row)

    def _get_workflow_version(self, version_id: str) -> WorkflowVersion:
        with self._connect() as conn:
            row = conn.execute("select * from workflow_versions where id = %s", (version_id,)).fetchone()
        if row is None:
            raise KeyError(version_id)
        return self._row_to_workflow_version(row)

    def _get_update_application(self, application_id: str) -> UpdateApplicationRecord:
        with self._connect() as conn:
            row = conn.execute("select * from update_applications where id = %s", (application_id,)).fetchone()
        if row is None:
            raise KeyError(application_id)
        return self._row_to_update_application(row)

    def _row_to_run(self, row: dict[str, Any]) -> RunRecord:
        return RunRecord(
            id=row["id"],
            status=row["status"],
            phase=row["phase"],
            requestedDepth=row["requested_depth"],
            intake=row["intake"],
            progress=row["progress"],
            resultMarkdown=row["result_markdown"],
            error=row["error"],
            createdAt=row["created_at"],
            updatedAt=row["updated_at"],
        )

    def _row_to_update(self, row: dict[str, Any]) -> ProposedUpdate:
        return ProposedUpdate(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            status=row["status"],
            body=row["body"],
            evidenceRunIds=_loads(row["evidence_run_ids"]),
            createdAt=row["created_at"],
            updatedAt=row["updated_at"],
            approvedAt=row["approved_at"],
            declinedAt=row["declined_at"],
        )

    def _row_to_workflow_version(self, row: dict[str, Any]) -> WorkflowVersion:
        return WorkflowVersion(
            id=row["id"],
            version=row["version"],
            status=row["status"],
            notes=row["notes"],
            instructionSummary=row["instruction_summary"],
            sourcePolicy=row["source_policy"],
            createdAt=row["created_at"],
            approvedAt=row["approved_at"],
        )

    def _row_to_update_application(self, row: dict[str, Any]) -> UpdateApplicationRecord:
        return UpdateApplicationRecord(
            id=row["id"],
            updateId=row["update_id"],
            category=row["category"],
            status=row["status"],
            summary=row["summary"],
            memoryKey=row["memory_key"],
            artifactKey=row["artifact_key"],
            workflowVersion=row["workflow_version"],
            createdAt=row["created_at"],
        )

    def _row_to_evaluation_result(self, row: dict[str, Any]) -> EvaluationResult:
        return EvaluationResult(
            id=row["id"],
            caseId=row["case_id"],
            status=row["status"],
            score=float(row["score"]),
            summary=row["summary"],
            runId=row["run_id"],
            evidence=_loads(row["evidence"]),
            artifactKey=row["artifact_key"],
            createdAt=row["created_at"],
        )


def _source_params(run_id: str, source: SourceRecord, *, sqlite: bool) -> tuple[Any, ...]:
    params = (
        source.id,
        run_id,
        source.title,
        source.url,
        source.source_type,
        source.author,
        source.channel_name,
        source.published_date,
        source.confidence,
        source.confidence_reason,
        source.relevance,
        source.transcript_status,
        source.artifact_key,
        source.notes,
    )
    if sqlite:
        return (*params, _iso_now())
    return params


def _artifact_params(run_id: str, artifact: ArtifactRecord) -> tuple[Any, ...]:
    return (
        artifact.id,
        run_id,
        artifact.kind,
        artifact.label,
        artifact.key,
        artifact.url,
        artifact.content_type,
        artifact.notes,
        artifact.created_at.isoformat(),
    )


def create_repository(database_url: str | None, local_sqlite_path: str) -> RunRepository:
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        return PostgresRunRepository(database_url)
    return LocalSQLiteRunRepository(local_sqlite_path)
