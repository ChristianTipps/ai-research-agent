from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .schemas import (
    FeedbackCreate,
    ResearchIntake,
    RunProgress,
    RunRecord,
    RunStatus,
    SourceRecord,
    WorkflowPhase,
    initial_progress,
    now_utc,
)


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
    def save_locations(
        self,
        run_id: str,
        *,
        notion_prompt_url: str | None = None,
        notion_response_url: str | None = None,
        spaces_summary_key: str | None = None,
    ) -> RunRecord: ...
    def save_feedback(self, run_id: str, feedback: FeedbackCreate) -> None: ...


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


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
                """
            )

    def create_run(self, intake: ResearchIntake) -> RunRecord:
        run_id = _new_run_id()
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
                      id, run_id, title, url, published_date, confidence, notes, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.id,
                        run_id,
                        source.title,
                        source.url,
                        source.published_date,
                        source.confidence,
                        source.notes,
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
    ) -> RunRecord:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        existing = current.progress.saved_locations
        current.progress.saved_locations.notion_prompt_url = (
            notion_prompt_url or existing.notion_prompt_url
        )
        current.progress.saved_locations.notion_response_url = (
            notion_response_url or existing.notion_response_url
        )
        current.progress.saved_locations.spaces_summary_key = (
            spaces_summary_key or existing.spaces_summary_key
        )
        with self._connect() as conn:
            conn.execute(
                """
                update research_runs
                set notion_prompt_url = coalesce(?, notion_prompt_url),
                    notion_response_url = coalesce(?, notion_response_url),
                    spaces_summary_key = coalesce(?, spaces_summary_key),
                    progress = ?,
                    updated_at = ?
                where id = ?
                """,
                (
                    notion_prompt_url,
                    notion_response_url,
                    spaces_summary_key,
                    current.progress.model_dump_json(by_alias=True),
                    _iso_now(),
                    run_id,
                ),
            )
        return self.get_run(run_id)  # type: ignore[return-value]

    def save_feedback(self, run_id: str, feedback: FeedbackCreate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into agent_feedback (run_id, rating, comment, created_at)
                values (?, ?, ?, ?)
                """,
                (run_id, feedback.rating, feedback.comment, _iso_now()),
            )

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
            createdAt=datetime.fromisoformat(data["created_at"]),
            updatedAt=datetime.fromisoformat(data["updated_at"]),
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
                """
            )

    def create_run(self, intake: ResearchIntake) -> RunRecord:
        run_id = _new_run_id()
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
                    self.Jsonb(intake.model_dump(by_alias=True)),
                    self.Jsonb(progress.model_dump(by_alias=True)),
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
                    self.Jsonb((progress or current.progress).model_dump(by_alias=True)),
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
                      id, run_id, title, url, published_date, confidence, notes
                    ) values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (id) do update set
                      title = excluded.title,
                      url = excluded.url,
                      published_date = excluded.published_date,
                      confidence = excluded.confidence,
                      notes = excluded.notes
                    """,
                    (
                        source.id,
                        run_id,
                        source.title,
                        source.url,
                        source.published_date,
                        source.confidence,
                        source.notes,
                    ),
                )

    def save_locations(
        self,
        run_id: str,
        *,
        notion_prompt_url: str | None = None,
        notion_response_url: str | None = None,
        spaces_summary_key: str | None = None,
    ) -> RunRecord:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        existing = current.progress.saved_locations
        current.progress.saved_locations.notion_prompt_url = (
            notion_prompt_url or existing.notion_prompt_url
        )
        current.progress.saved_locations.notion_response_url = (
            notion_response_url or existing.notion_response_url
        )
        current.progress.saved_locations.spaces_summary_key = (
            spaces_summary_key or existing.spaces_summary_key
        )
        with self._connect() as conn:
            conn.execute(
                """
                update research_runs
                set notion_prompt_url = coalesce(%s, notion_prompt_url),
                    notion_response_url = coalesce(%s, notion_response_url),
                    spaces_summary_key = coalesce(%s, spaces_summary_key),
                    progress = %s,
                    updated_at = now()
                where id = %s
                """,
                (
                    notion_prompt_url,
                    notion_response_url,
                    spaces_summary_key,
                    self.Jsonb(current.progress.model_dump(by_alias=True)),
                    run_id,
                ),
            )
        return self.get_run(run_id)  # type: ignore[return-value]

    def save_feedback(self, run_id: str, feedback: FeedbackCreate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into agent_feedback (run_id, rating, comment)
                values (%s, %s, %s)
                """,
                (run_id, feedback.rating, feedback.comment),
            )

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


def create_repository(database_url: str | None, local_sqlite_path: str) -> RunRepository:
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        return PostgresRunRepository(database_url)
    return LocalSQLiteRunRepository(local_sqlite_path)
