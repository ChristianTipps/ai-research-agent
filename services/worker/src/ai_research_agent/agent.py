from __future__ import annotations

import os
import textwrap
from typing import Any

from .schemas import ResearchIntake, SourceStrategy
from .source_strategy import resolve_research_budget_minutes

try:
    from agents import Agent, Runner, WebSearchTool
except ImportError:  # pragma: no cover - import is verified in environment checks
    Agent = None  # type: ignore[assignment]
    Runner = None  # type: ignore[assignment]
    WebSearchTool = None  # type: ignore[assignment]


BASE_INSTRUCTIONS = """
You are an AI Research Agent for learning and building in AI, Codex, software agents,
prompt design, automation, and related tools.

Core formula:
Agent = Goal + Instructions + Tools + Context + Memory + Feedback Loop + Limits

Behavior:
- Validate that the research request is specific and grounded in the user's stated goal.
- Use current, credible, relevant sources when the topic may have changed.
- Discover sources automatically. The user should not need to tell you which
  sources to include; evaluate source credibility yourself.
- Treat deep research as a thesis, antithesis, and synthesis process: identify
  the strongest case, strongest counterpoint, and the most useful integrated view.
- Prefer primary sources, official docs, release notes, research papers, GitHub repos,
  and direct company announcements.
- Use YouTube or creator sources when the user asks for them or when creator
  practice/opinion materially improves the research. Clearly label those as
  creator/community perspective unless corroborated by primary sources.
- Compare sources and separate confirmed facts from reasonable guesses.
- Track dates carefully when recency affects relevance.
- Avoid hype and unsupported certainty.
- Avoid inline citation clutter in sections 1-9. Mention source names naturally,
  but put every source URL only in section 10.
- Do not add parenthetical source-domain markers like "(platform.openai.com)" in
  the body. Keep links in the final source list.
- Do not expose hidden chain-of-thought. Use concise reasoning summaries, decisions,
  source notes, assumptions, and next steps.
- Do not claim that Notion or DigitalOcean records were saved. The backend appends the
  saved-records section after persistence finishes.

Produce the final answer with these sections:
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

Section 10 requirements:
- Group source URLs at the end only.
- Include enough source metadata to make credibility clear: source name, URL,
  source type, and why it is trustworthy or limited.
- If YouTube videos are used, include channel/video metadata when available and say
  whether transcript access was available or unavailable.
- Do not repeat source links in earlier sections.
"""


def build_research_prompt(
    intake: ResearchIntake,
    source_strategy: SourceStrategy | None = None,
    approved_update_context: str = "",
) -> str:
    strategy = source_strategy.model_dump(by_alias=True) if source_strategy else {}
    budget = resolve_research_budget_minutes(intake)
    return textwrap.dedent(
        f"""
        Research request:

        Niche Research topic: {intake.niche_research_topic}
        Why I care: {intake.why_i_care}
        I want to use this for: {intake.intended_use}
        How deep/long should the research be: {intake.custom_depth or intake.depth}
        Research budget effort target: {budget} minutes

        Optional context:
        - My current skill level: {intake.current_skill_level or "Not provided"}
        - Deadline or urgency: {intake.deadline or "Not provided"}
        - Output type: {intake.output_type or "Not provided"}

        Approved runtime updates:
        {approved_update_context or "- No approved update notes yet."}

        Source strategy:
        - Use this source strategy object as the plan: {strategy}
        - Search broadly enough for the requested depth, budget, and topic volatility.
        - Check source credibility yourself instead of relying on user-provided source lists.
        - Prefer primary and authoritative sources, then corroborate with credible secondary sources.
        - Include creator/YouTube sources when the strategy requests them.
        - Reject weak, stale, promotional, or unsupported sources unless you are explicitly comparing them.
        - Keep all source URLs in the final "Sources and confidence" section only.

        Depth behavior:
        - Quick scan: 5-10 bullets, 3-5 sources, clear answer.
        - Standard brief: structured sections, 5-10 sources, recommendations, exercise, quiz.
        - Deep research: 10-20 sources, compare viewpoints, timeline, risks, roadmap.
        - Technical deep dive: implementation patterns, APIs, repos, evals, failure modes, testing plan.

        Synthesis behavior:
        - Include a clear thesis, antithesis, and synthesis.
        - Adjust assumptions and definitions to the user's skill level.
        - Put links only in section 10; body sections should be readable in Notion.

        If source access is incomplete, say exactly what is missing.
        """
    ).strip()


def create_research_agent(model: str, enable_web_search: bool = True) -> Any:
    if Agent is None:
        raise RuntimeError("openai-agents is not installed")

    tools: list[Any] = []
    if enable_web_search and WebSearchTool is not None:
        tools.append(WebSearchTool(search_context_size="medium"))

    return Agent(
        name="AI Research Agent",
        instructions=BASE_INSTRUCTIONS,
        model=model,
        tools=tools,
    )


async def run_research_agent(
    intake: ResearchIntake,
    model: str,
    enable_web_search: bool,
    source_strategy: SourceStrategy | None = None,
    approved_update_context: str = "",
) -> str:
    if Runner is None:
        raise RuntimeError("openai-agents is not installed")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to run the research agent")

    agent = create_research_agent(model=model, enable_web_search=enable_web_search)
    result = await Runner.run(
        agent,
        build_research_prompt(
            intake,
            source_strategy=source_strategy,
            approved_update_context=approved_update_context,
        ),
    )
    return str(result.final_output)
