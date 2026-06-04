from __future__ import annotations

import os
import textwrap
from typing import Any

from .schemas import ResearchIntake

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
- Prefer primary sources, official docs, release notes, research papers, GitHub repos,
  and direct company announcements.
- Compare sources and separate confirmed facts from reasonable guesses.
- Track dates carefully when recency affects relevance.
- Avoid hype and unsupported certainty.
- Do not expose hidden chain-of-thought. Use concise reasoning summaries, decisions,
  source notes, assumptions, and next steps.
- Do not claim that Notion or DigitalOcean records were saved. The backend appends the
  saved-records section after persistence finishes.

Produce the final answer with these sections:
# 1. Simple explanation
# 2. Why this matters right now
# 3. Facts vs guesses
# 4. Current and durable context
# 5. Useful tools, platforms, people, companies, and examples
# 6. Practical ways I can use this
# 7. Knowledge gaps you noticed
# 8. One small exercise
# 9. Light quiz
# 10. Sources and confidence

End with the feedback question:
"Was this too basic, too advanced, or about right?"
"""


def build_research_prompt(intake: ResearchIntake) -> str:
    return textwrap.dedent(
        f"""
        Research request:

        Niche Research topic: {intake.niche_research_topic}
        Why I care: {intake.why_i_care}
        I want to use this for: {intake.intended_use}
        How deep/long should the research be: {intake.custom_depth or intake.depth}

        Optional context:
        - My current skill level: {intake.current_skill_level or "Not provided"}
        - Preferred format: {intake.preferred_format or "Not provided"}
        - Sources I trust or want included: {intake.trusted_sources or "Not provided"}
        - Sources I want excluded: {intake.excluded_sources or "Not provided"}
        - Deadline: {intake.deadline or "Not provided"}
        - Output type: {intake.output_type or "Not provided"}

        Depth behavior:
        - Quick scan: 5-10 bullets, 3-5 sources, clear answer.
        - Standard brief: structured sections, 5-10 sources, recommendations, exercise, quiz.
        - Deep research: 10-20 sources, compare viewpoints, timeline, risks, roadmap.
        - Technical deep dive: implementation patterns, APIs, repos, evals, failure modes, testing plan.

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


async def run_research_agent(intake: ResearchIntake, model: str, enable_web_search: bool) -> str:
    if Runner is None:
        raise RuntimeError("openai-agents is not installed")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to run the research agent")

    agent = create_research_agent(model=model, enable_web_search=enable_web_search)
    result = await Runner.run(agent, build_research_prompt(intake))
    return str(result.final_output)
