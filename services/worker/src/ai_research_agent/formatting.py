from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .schemas import SourceRecord


MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
URL_RE = re.compile(r"https?://[^\s)\]]+")
DOMAIN_PAREN_RE = re.compile(
    r"\s*\(((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:\s*,\s*(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})*)\)"
)
SOURCES_HEADING_RE = re.compile(r"^#{1,3}\s*(?:\d+\.\s*)?Sources(?:\s+and\s+confidence)?\s*$", re.I)
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def strip_tracking_params(url: str) -> str:
    split = urlsplit(url.rstrip(".,;"))
    query = urlencode(
        [(key, value) for key, value in parse_qsl(split.query, keep_blank_values=True) if key not in TRACKING_PARAMS]
    )
    return urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))


def prepare_final_report(markdown: str, sources: list[SourceRecord]) -> str:
    body = _remove_existing_sources_section(markdown)
    body = _remove_inline_source_clutter(body).strip()
    return f"{body}\n\n{_build_source_section(sources)}".strip()


def _remove_existing_sources_section(markdown: str) -> str:
    lines = markdown.splitlines()
    kept: list[str] = []
    skip = False
    for line in lines:
        if SOURCES_HEADING_RE.match(line.strip()):
            skip = True
            continue
        if skip:
            continue
        kept.append(line)
    return "\n".join(kept)


def _remove_inline_source_clutter(markdown: str) -> str:
    without_links = MARKDOWN_LINK_RE.sub(lambda match: match.group(1), markdown)
    without_urls = URL_RE.sub("", without_links)
    without_domains = DOMAIN_PAREN_RE.sub("", without_urls)
    without_extra_spaces = re.sub(r"[ \t]+([.,;:!?])", r"\1", without_domains)
    without_extra_spaces = re.sub(r"\(\s*\)", "", without_extra_spaces)
    return re.sub(r"\n{3,}", "\n\n", without_extra_spaces)


def _build_source_section(sources: list[SourceRecord]) -> str:
    section = ["# 10. Sources and confidence", "", "## Source links"]
    if not sources:
        section.append("- No source URLs were returned by the research run.")
    else:
        for source in _dedupe_sources(sources):
            label = source.title.strip() or source.url or "Source"
            label = _clean_source_label(label)
            if source.url:
                section.append(f"- [{label}]({strip_tracking_params(source.url)}) — {source.confidence} confidence")
            else:
                section.append(f"- {label} — {source.confidence} confidence")
    section.extend(
        [
            "",
            "## Confidence",
            "Confidence reflects source authority, recency, corroboration, and relevance to the requested depth.",
        ]
    )
    return "\n".join(section)


def _dedupe_sources(sources: list[SourceRecord]) -> list[SourceRecord]:
    seen: set[str] = set()
    result: list[SourceRecord] = []
    for source in sources:
        key = strip_tracking_params(source.url) if source.url else source.title
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def _clean_source_label(label: str) -> str:
    label = _remove_inline_source_clutter(label)
    label = re.sub(r"^\s*[-*#0-9.\s]+", "", label).strip()
    return label[:140] or "Source"
