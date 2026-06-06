# AI Research Agent

Learning-centered research agent that uses:

- Vercel and Next.js for the mobile-friendly control surface.
- DigitalOcean for the long-running agent runtime, database, operating memory, artifact storage, persistence, and future scheduling.
- OpenAI Agents SDK for staged research synthesis.
- Notion for readable prompt and response records that support learning, highlighting, and explanation.

The local workspace is only for development. Production operation should come from a GitHub repository deployed to Vercel and DigitalOcean.

## Product Shape

The app is organized around three connected systems:

- **Research Engine**: normalizes intake, plans topic-aware source strategy, performs source discovery, reviews source quality, compares thesis/antithesis/synthesis, and writes the final report.
- **Learning Workspace**: creates Notion-friendly reports with clean titles, readable sections, source links grouped at the end, and formatting that works well with Notion AI Explain.
- **Memory/Evaluation Layer**: stores source artifacts, run summaries, trust reports, feedback, proposed update notes, approved workflow versions, operating instructions, tool configs, and evaluation evidence in DigitalOcean.

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
- DigitalOcean Spaces stores final reports, source artifacts, best-effort YouTube transcript artifacts, trust reports, instruction files, tool configs, eval cases/results, run summaries, source snapshots, and workflow definitions.
- User feedback is stored as pending proposed updates. Runtime changes are applied only after an admin authorizes them on the versions/updates page.
- Do not store hidden chain-of-thought, secrets, or raw credentials in Notion, logs, prompts, or source code.

See [docs/deployment.md](docs/deployment.md) for the production checklist.
