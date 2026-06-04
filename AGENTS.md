# Project Agent Rules

This project is an AI Research Agent with a Vercel frontend and DigitalOcean backend.

- Keep production behavior independent of this local machine.
- Treat Vercel as the user-facing control surface, not the long-running research runtime.
- Keep OpenAI Agents SDK logic in `services/worker`.
- Validate the four required intake fields before starting full research.
- Store only concise reasoning summaries, decisions, tool summaries, source notes, errors, and next steps.
- Never commit secrets. `.env.local` and other `.env*` files are ignored.
- Prefer primary sources and date-sensitive verification for research topics.
