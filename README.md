# AI Research Agent

Production-oriented starter for a research agent that uses:

- Vercel and Next.js for the mobile-friendly control surface.
- DigitalOcean for the long-running agent runtime, storage, persistence, and scheduling.
- OpenAI Agents SDK for the research workflow.
- Notion for readable prompt and response records.

The local workspace is only for development. Production operation should come from a GitHub repository deployed to Vercel and DigitalOcean.

## Repository Shape

```text
apps/web/             Next.js App Router UI and short Vercel API routes
services/worker/      FastAPI worker service using the OpenAI Agents SDK
packages/shared/      Shared TypeScript contracts for the web app
infra/                DigitalOcean app config, database schema, storage notes
docs/                 Architecture, deployment, and prompt policy docs
```

## Local Setup

1. Copy `.env.example` to `.env.local` for local secrets.
2. Install web dependencies with `pnpm install`.
3. Install worker dependencies:

   ```bash
   cd services/worker
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -e ".[dev]"
   ```

4. Start the worker:

   ```bash
   cd services/worker
   python -m ai_research_agent.main
   ```

5. Start the web app:

   ```bash
   pnpm --dir apps/web dev
   ```

## Production Notes

- Vercel should host only the UI, short API routes, status reads, and job-start handoff.
- DigitalOcean should run the long-lived worker service and own durable state.
- Notion stores submitted prompts and final readable responses only.
- DigitalOcean Spaces stores artifacts, instruction files, run summaries, source snapshots, and workflow definitions.
- Do not store hidden chain-of-thought, secrets, or raw credentials in Notion, logs, prompts, or source code.

See [docs/deployment.md](docs/deployment.md) for the production checklist.
