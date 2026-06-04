from __future__ import annotations

import re
import uuid

from .schemas import SourceRecord


URL_RE = re.compile(r"https?://[^\s)\]]+")


def extract_sources(markdown: str) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    seen: set[str] = set()
    for line in markdown.splitlines():
        for url in URL_RE.findall(line):
            normalized = url.rstrip(".,")
            if normalized in seen:
                continue
            seen.add(normalized)
            title = line.strip("- *#0123456789. ").strip()[:140] or normalized
            confidence = "medium"
            lower = line.lower()
            if "official" in lower or "primary" in lower or "docs" in lower:
                confidence = "high"
            elif "rumor" in lower or "reddit" in lower or "unconfirmed" in lower:
                confidence = "low"
            records.append(
                SourceRecord(
                    id=f"src_{uuid.uuid4().hex[:10]}",
                    title=title,
                    url=normalized,
                    confidence=confidence,  # type: ignore[arg-type]
                    notes="Extracted from final research response.",
                )
            )
    return records
