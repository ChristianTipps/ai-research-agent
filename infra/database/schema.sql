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
  final_report_key text,
  trust_report_key text,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists source_records (
  id text primary key,
  run_id text not null references research_runs(id) on delete cascade,
  title text not null,
  url text,
  source_type text not null default 'web',
  author text,
  channel_name text,
  published_date text,
  confidence text not null,
  confidence_reason text,
  relevance text,
  transcript_status text not null default 'not_applicable',
  artifact_key text,
  notes text,
  created_at timestamptz not null default now()
);

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
