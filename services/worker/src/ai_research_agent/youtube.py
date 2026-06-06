from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .schemas import SourceRecord


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


@dataclass
class YouTubeArtifact:
    source_id: str
    video_id: str
    metadata: dict[str, str]
    transcript: str | None
    transcript_status: str


def extract_video_id(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in YOUTUBE_HOSTS:
        return None
    if host == "youtu.be":
        return parsed.path.strip("/") or None
    query = parse_qs(parsed.query)
    if "v" in query:
        return query["v"][0]
    match = re.search(r"/(?:shorts|embed)/([^/?#]+)", parsed.path)
    if match:
        return match.group(1)
    return None


async def collect_youtube_artifact(source: SourceRecord) -> YouTubeArtifact | None:
    video_id = extract_video_id(source.url)
    if not video_id:
        return None
    metadata = await _fetch_oembed(source.url)
    transcript = await _fetch_public_transcript(video_id)
    status = "available" if transcript else "transcript_unavailable"
    return YouTubeArtifact(
        source_id=source.id,
        video_id=video_id,
        metadata=metadata,
        transcript=transcript,
        transcript_status=status,
    )


async def _fetch_oembed(url: str | None) -> dict[str, str]:
    if not url:
        return {}
    endpoint = f"https://www.youtube.com/oembed?{urlencode({'format': 'json', 'url': url})}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return {
                key: str(data[key])
                for key in ("title", "author_name", "author_url", "provider_name")
                if key in data
            }
    except Exception:  # noqa: BLE001
        return {}


async def _fetch_public_transcript(video_id: str) -> str | None:
    # Best-effort public timedtext only: no cookies, no private session, no video download.
    endpoint = "https://www.youtube.com/api/timedtext"
    params = {"v": video_id, "lang": "en"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(endpoint, params=params)
            if response.status_code >= 400 or not response.text.strip():
                return None
            root = ET.fromstring(response.text)
            chunks = []
            for node in root.findall(".//text"):
                if node.text:
                    chunks.append(html.unescape(node.text.strip()))
            text = " ".join(chunk for chunk in chunks if chunk)
            return text[:12000] or None
    except Exception:  # noqa: BLE001
        return None
