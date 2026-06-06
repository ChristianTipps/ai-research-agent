from __future__ import annotations

import re
import uuid

from .formatting import strip_tracking_params
from .schemas import SourceRecord
from .source_strategy import classify_source_type, review_source_record


URL_RE = re.compile(r"https?://[^\s)\]]+")


def extract_sources(markdown: str) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    seen: set[str] = set()
    for line in markdown.splitlines():
        for url in URL_RE.findall(line):
            normalized = strip_tracking_params(url)
            if normalized in seen:
                continue
            seen.add(normalized)
            title = _source_title(line, normalized)
            lower = line.lower()
            confidence = "medium"
            confidence_reason = "Extracted from final research response."
            if any(term in lower for term in ["official", "primary", "docs", "documentation"]):
                confidence = "high"
                confidence_reason = "The response labeled this as official, primary, or documentation."
            elif any(term in lower for term in ["rumor", "unconfirmed", "anecdote"]):
                confidence = "low"
                confidence_reason = "The response labeled this as weak, unconfirmed, or anecdotal."
            record = SourceRecord(
                id=f"src_{uuid.uuid4().hex[:10]}",
                title=title,
                url=normalized,
                sourceType=classify_source_type(normalized, title),
                confidence=confidence,  # type: ignore[arg-type]
                confidenceReason=confidence_reason,
                transcriptStatus="not_attempted"
                if classify_source_type(normalized, title) == "youtube"
                else "not_applicable",
                notes="Extracted from final research response.",
            )
            records.append(review_source_record(record))
    return records


def _source_title(line: str, url: str) -> str:
    without_url = line.replace(url, "")
    without_markdown = re.sub(r"\[([^\]]+)\]\(\s*\)", r"\1", without_url)
    title = without_markdown.strip("- *#0123456789. —:").strip()
    return title[:140] or url
