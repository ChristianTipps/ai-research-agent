from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from .schemas import ResearchIntake, SourceRecord, SourceStrategy, SourceType, TrustReport


BUDGET_DEFAULTS = {
    "Quick scan": 2,
    "Standard brief": 5,
    "Deep research": 10,
    "Technical deep dive": 15,
    "Custom": 10,
}


def resolve_research_budget_minutes(intake: ResearchIntake) -> int:
    if intake.research_budget_minutes:
        return intake.research_budget_minutes
    custom = intake.custom_depth or ""
    match = re.search(r"\b(\d{1,2})\s*(?:min|minute|minutes)\b", custom, re.I)
    if match:
        return min(max(int(match.group(1)), 1), 60)
    return BUDGET_DEFAULTS[intake.depth]


def build_source_strategy(intake: ResearchIntake) -> SourceStrategy:
    budget = resolve_research_budget_minutes(intake)
    text = " ".join(
        [
            intake.niche_research_topic,
            intake.why_i_care,
            intake.intended_use,
            intake.custom_depth or "",
        ]
    ).lower()
    source_types: list[SourceType] = ["official", "documentation", "web"]
    targets = [
        "official documentation and announcements",
        "primary sources and release notes",
        "recent credible web coverage when the topic is current",
    ]

    if any(term in text for term in ["github", "repo", "code", "implementation", "sdk", "api"]):
        source_types.append("github")
        targets.append("GitHub repositories, issues, examples, or changelogs")
    if any(term in text for term in ["paper", "research", "study", "academic", "benchmark"]):
        source_types.append("research_paper")
        targets.append("research papers, benchmarks, and technical reports")
    if any(term in text for term in ["news", "latest", "today", "current", "recent", "2026"]):
        source_types.append("news")
        targets.append("date-stamped current sources")
    has_user_youtube_urls = bool(intake.youtube_urls)
    include_youtube = has_user_youtube_urls or any(
        term in text
        for term in [
            "youtube",
            "youtuber",
            "creator",
            "video",
            "tutorial",
            "opinion",
            "opinions",
            "codex",
        ]
    )
    if include_youtube:
        source_types.append("youtube")
        if has_user_youtube_urls:
            targets.append("user-submitted YouTube videos with metadata and best-effort public transcripts")
        targets.append("YouTube creator videos with metadata and best-effort public transcripts")
    if any(term in text for term in ["reddit", "community", "forum", "hacker news", "hn"]):
        source_types.append("community")
        targets.append("community discussion clearly labeled as opinion or anecdote")

    source_types = _dedupe(source_types)
    min_sources, max_sources = _source_window(intake.depth, budget)
    rationale = (
        f"Use {budget} minutes as an effort target: increase source diversity and review depth, "
        "but finish when quality criteria are met."
    )
    return SourceStrategy(
        requestedSourceTypes=source_types,
        requiredSourceTypes=["official", "web"] + (["youtube"] if include_youtube else []),
        sourceTargets=targets,
        minSources=min_sources,
        maxSources=max_sources,
        includeYouTube=include_youtube,
        rationale=rationale,
    )


def review_source_record(source: SourceRecord) -> SourceRecord:
    source.source_type = classify_source_type(source.url, source.title)
    if source.source_type in {"official", "documentation", "primary", "github", "research_paper"}:
        source.confidence = "high"
        source.confidence_reason = source.confidence_reason or "Primary or authoritative source."
    elif source.source_type in {"community", "youtube"}:
        source.confidence = "medium" if source.confidence != "low" else "low"
        source.confidence_reason = source.confidence_reason or (
            "Useful for perspective, but should be corroborated before treating claims as facts."
        )
    else:
        source.confidence_reason = source.confidence_reason or (
            "General web source; confidence depends on recency, corroboration, and relevance."
        )
    if source.source_type != "youtube":
        source.transcript_status = "not_applicable"
    return source


def classify_source_type(url: str | None, title: str = "") -> SourceType:
    haystack = f"{url or ''} {title}".lower()
    netloc = urlparse(url).netloc.lower() if url else ""
    if "youtube.com" in netloc or "youtu.be" in netloc:
        return "youtube"
    if "github.com" in netloc:
        return "github"
    if "arxiv.org" in netloc or "doi.org" in netloc or "acm.org" in netloc or "ieee.org" in netloc:
        return "research_paper"
    if any(domain in netloc for domain in ["docs.", "developer.", "developers."]):
        return "documentation"
    if any(domain in netloc for domain in ["openai.com", "google.com", "microsoft.com", "anthropic.com"]):
        return "official"
    if any(domain in netloc for domain in ["reddit.com", "news.ycombinator.com", "forum", "community"]):
        return "community"
    if any(term in haystack for term in ["official", "release notes", "changelog"]):
        return "primary"
    return "web"


def build_trust_report(sources: list[SourceRecord], strategy: SourceStrategy) -> TrustReport:
    if not sources:
        return TrustReport(
            overallConfidence="low",
            summary="No source URLs were extracted from the final report.",
            strengths=[],
            limitations=["The run needs follow-up because it produced no source records."],
            sourceMix=[],
            recommendations=["Retry with web search enabled or a narrower topic."],
        )

    counts = Counter(source.source_type for source in sources)
    high_count = sum(1 for source in sources if source.confidence == "high")
    required_missing = [
        source_type
        for source_type in strategy.required_source_types
        if not any(source.source_type == source_type for source in sources)
    ]
    overall = "high" if high_count >= max(2, len(sources) // 2) and not required_missing else "medium"
    if len(sources) < strategy.min_sources or required_missing:
        overall = "medium" if high_count else "low"

    strengths = []
    if high_count:
        strengths.append(f"{high_count} high-confidence source records were captured.")
    if strategy.include_youtube and counts.get("youtube", 0):
        strengths.append("YouTube/creator sources were included and labeled separately.")
    limitations = []
    if required_missing:
        limitations.append(f"Missing requested source types: {', '.join(required_missing)}.")
    if len(sources) < strategy.min_sources:
        limitations.append(
            f"Extracted {len(sources)} sources, below the {strategy.min_sources}-source target."
        )
    if strategy.include_youtube and not counts.get("youtube", 0):
        limitations.append("The run requested YouTube sources but none were extracted.")

    return TrustReport(
        overallConfidence=overall,  # type: ignore[arg-type]
        summary="Source trust was reviewed from authority, source type, diversity, and requested coverage.",
        strengths=strengths or ["Sources were extracted and typed for review."],
        limitations=limitations,
        sourceMix=[f"{source_type}: {count}" for source_type, count in sorted(counts.items())],
        recommendations=[
            "Use community and creator sources as perspective, not standalone factual proof.",
            "Prefer primary dated sources for claims about product behavior or APIs.",
        ],
    )


def _source_window(depth: str, budget: int) -> tuple[int, int]:
    if depth == "Quick scan":
        return 3, max(5, min(8, budget + 3))
    if depth == "Standard brief":
        return 5, max(10, min(14, budget * 2))
    if depth == "Deep research":
        return 10, max(15, min(24, budget * 2))
    if depth == "Technical deep dive":
        return 10, max(16, min(28, budget * 2))
    return 6, max(12, min(24, budget * 2))


def _dedupe(values: list[SourceType]) -> list[SourceType]:
    result: list[SourceType] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
