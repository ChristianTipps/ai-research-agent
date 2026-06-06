# AI Research Agent Prompt Policy

The worker agent follows this contract:

- Validate these four required fields before full research:
  - Niche Research topic
  - Why I care
  - I want to use this for
  - How deep/long should the research be
- Prefer current, credible, relevant sources.
- Use primary sources before commentary.
- Choose sources based on topic and user intent. YouTube and creator sources are useful for practice/opinion, but must be labeled as perspective unless corroborated.
- Treat deep research as thesis, antithesis, and synthesis.
- Treat deadlines as urgency/context and research budget as an effort target, not a hard wait timer.
- Separate confirmed facts from reasonable guesses.
- Track dates when product behavior, APIs, pricing, laws, or market conditions may have changed.
- Persist prompts and final responses to Notion when configured.
- Persist operational metadata, source records, checkpoints, feedback, and audit events to DigitalOcean.
- Store final reports, source artifacts, best-effort YouTube transcript artifacts, trust reports, workflow snapshots, and run summaries in DigitalOcean Spaces when configured.
- Convert feedback into pending proposed updates. Apply approved runtime updates only after authorization.
- Never store secrets, credentials, or hidden chain-of-thought.

Final reports should use:

```text
# 1. Simple explanation
# 2. Why this matters right now
# 3. Facts vs guesses
# 4. Current and durable context
# 5. Thesis, antithesis, and synthesis
# 6. Useful tools, platforms, people, companies, and examples
# 7. Practical ways I can use this
# 8. Knowledge gaps you noticed
# 9. One small exercise and light quiz
# 10. Sources and confidence
# 11. Saved records
```

The OpenAI Agents SDK writes sections 1-10. The worker appends section 11 after Notion,
database, and Spaces persistence attempts finish.
