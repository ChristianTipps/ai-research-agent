from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .schemas import ResearchIntake


INLINE_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`")
MAX_RICH_TEXT_CHARS = 1800
MAX_CHILDREN_PER_REQUEST = 90


def _plain_text_chunks(text: str) -> list[dict]:
    return [
        {
            "type": "text",
            "text": {"content": chunk},
        }
        for chunk in _split_text(text)
    ] or [{"type": "text", "text": {"content": " "}}]


def _rich_text_from_markdown(text: str) -> list[dict]:
    result: list[dict] = []
    last_index = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > last_index:
            result.extend(_rich_text_chunks(text[last_index : match.start()]))
        if match.group(1) and match.group(2):
            result.extend(_rich_text_chunks(match.group(1), href=match.group(2)))
        elif match.group(3):
            result.extend(_rich_text_chunks(match.group(3), bold=True))
        elif match.group(4):
            result.extend(_rich_text_chunks(match.group(4), code=True))
        last_index = match.end()
    if last_index < len(text):
        result.extend(_rich_text_chunks(text[last_index:]))
    return result or [{"type": "text", "text": {"content": " "}}]


def _rich_text_chunks(
    text: str,
    *,
    bold: bool = False,
    code: bool = False,
    href: str | None = None,
) -> list[dict]:
    chunks: list[dict] = []
    annotations = {
        "bold": bold,
        "italic": False,
        "strikethrough": False,
        "underline": False,
        "code": code,
        "color": "default",
    }
    for chunk in _split_text(text):
        text_payload: dict[str, str] = {"content": chunk}
        if href:
            text_payload["link"] = {"url": href}  # type: ignore[assignment]
        item = {
            "type": "text",
            "text": text_payload,
            "annotations": annotations,
        }
        if href:
            item["href"] = href
        chunks.append(item)
    return chunks


def _split_text(text: str) -> list[str]:
    if not text:
        return []
    return [text[index : index + MAX_RICH_TEXT_CHARS] for index in range(0, len(text), MAX_RICH_TEXT_CHARS)]


def _text_block(block_type: str, text: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": _rich_text_from_markdown(text)},
    }


def _code_blocks(text: str) -> list[dict]:
    return [
        {
            "object": "block",
            "type": "code",
            "code": {"rich_text": _plain_text_chunks(chunk), "language": "plain text"},
        }
        for chunk in _split_text(text)
    ] or [_text_block("paragraph", " ")]


def _markdown_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        blocks.append(_text_block("paragraph", "\n".join(paragraph_lines).strip()))
        paragraph_lines.clear()

    def flush_code() -> None:
        if not code_lines:
            return
        blocks.extend(_code_blocks("\n".join(code_lines).rstrip()))
        code_lines.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            flush_paragraph()
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            block_type = {1: "heading_1", 2: "heading_2", 3: "heading_3"}[len(heading.group(1))]
            blocks.append(_text_block(block_type, heading.group(2)))
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            blocks.append(_text_block("bulleted_list_item", bullet.group(1)))
            continue

        numbered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if numbered:
            flush_paragraph()
            blocks.append(_text_block("numbered_list_item", numbered.group(1)))
            continue

        paragraph_lines.append(stripped)

    if in_code:
        flush_code()
    flush_paragraph()
    return blocks or [_text_block("paragraph", "No content.")]


@dataclass
class NotionClient:
    api_key: str | None
    prompts_database_id: str | None
    responses_database_id: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.prompts_database_id and self.responses_database_id)

    async def save_prompt(self, run_id: str, intake: ResearchIntake) -> str | None:
        if not self.enabled:
            return None
        title = f"{intake.niche_research_topic[:80]} - {run_id}"
        body = intake.model_dump_json(by_alias=True, indent=2)
        return await self._create_page(self.prompts_database_id, title, body)

    async def save_response(self, run_id: str, intake: ResearchIntake, markdown: str) -> str | None:
        if not self.enabled:
            return None
        title = f"Response: {intake.niche_research_topic[:70]} - {run_id}"
        return await self._create_page(self.responses_database_id, title, markdown)

    async def _create_page(self, database_id: str | None, title: str, markdown: str) -> str | None:
        if not database_id or not self.api_key:
            return None

        blocks = _markdown_blocks(markdown)
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title},
                        }
                    ]
                }
            },
            "children": blocks[:MAX_CHILDREN_PER_REQUEST],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.notion.com/v1/pages", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            page_id = data.get("id")
            if page_id:
                for start in range(MAX_CHILDREN_PER_REQUEST, len(blocks), MAX_CHILDREN_PER_REQUEST):
                    append_response = await client.patch(
                        f"https://api.notion.com/v1/blocks/{page_id}/children",
                        json={"children": blocks[start : start + MAX_CHILDREN_PER_REQUEST]},
                        headers=headers,
                    )
                    append_response.raise_for_status()
            return data.get("url") or page_id
