# Project Agent Rules

This project is a learning-centered AI Research Agent with three connected systems:

- Research Engine: staged source strategy, source discovery, credibility review, thesis/antithesis/synthesis, and final synthesis.
- Learning Workspace: Notion-ready prompt and response records optimized for reading, highlighting, explaining, and revisiting.
- Memory/Evaluation Layer: DigitalOcean database and Spaces records for run summaries, source artifacts, trust reports, feedback, proposed updates, workflow versions, and evaluation evidence.

Core rules:

- Keep production behavior independent of this local machine.
- Treat Vercel as the user-facing control surface, not the long-running research runtime.
- Keep OpenAI Agents SDK logic in `services/worker`.
- Validate the four required intake fields before starting full research.
- Treat `deadline` as urgency/context and `researchBudgetMinutes` as an effort target, not a hard wait timer.
- Prefer primary, current, and topic-appropriate sources; include YouTube/creator sources when requested or materially useful, and label them as perspective unless corroborated.
- Deep research should compare thesis, antithesis, and synthesis.
- Store only concise reasoning summaries, decisions, tool summaries, source notes, errors, trust reports, proposed updates, and next steps.
- Never store hidden chain-of-thought, secrets, raw credentials, or `.env*` values in code, logs, Notion, Spaces, or prompts.
- Feedback must become pending proposed updates. Do not apply instruction, workflow, source-policy, preference, or UI changes until authorized.
- Approved runtime updates must be versioned so future runs can explain which update influenced behavior.
