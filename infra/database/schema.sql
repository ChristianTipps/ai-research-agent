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
