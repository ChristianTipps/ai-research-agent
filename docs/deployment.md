# Deployment

## GitHub

1. Create a GitHub repository for this project.
2. Push all source code, schema files, deployment config, and docs.
3. Do not push `.env.local` or any other secret-bearing file.
4. Configure Codex Cloud against the GitHub repository so work can continue while your local computer is off.

## Vercel

Deploy `apps/web` as the frontend project.

Required environment variables:
- `AGENT_BACKEND_URL`
- `AGENT_BACKEND_TOKEN`

Vercel should call the DigitalOcean backend for job creation and status reads. It should not run long research jobs inside Vercel functions.

## DigitalOcean

Provision:
- App Platform service, Droplet, or Kubernetes service for `services/worker`.
- Managed PostgreSQL database.
- Spaces bucket `ai-research-agent-kb-a01bd200` in region `sfo3` when available.
- Environment variables listed in `.env.example`.

Apply the schema in `infra/database/schema.sql`.

Recommended App Platform config lives in `infra/digitalocean/app.yaml`.

## Notion

Create two databases:
- Research Prompts
- Research Responses

Add the database IDs and integration token to the DigitalOcean worker environment. Do not store secrets in Notion pages.

## End-to-End Verification

Before calling this production-ready:

1. Submit a research request from the Vercel app.
2. Confirm the DigitalOcean worker creates a run and advances phases.
3. Confirm the final response appears in the Vercel UI.
4. Confirm prompt and final response records are created in Notion.
5. Confirm run summaries or artifacts appear in DigitalOcean Spaces.
6. Confirm source metadata and feedback are persisted in the database.
7. Test retry, cancel, and feedback controls.
