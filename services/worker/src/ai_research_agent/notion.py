from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .schemas import MemoryContext, ResearchIntake


INLINE_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`")
MAX_RICH_TEXT_CHARS = 1800
MAX_CHILDREN_PER_REQUEST = 90
CODE_LANGS = {
    "bash",
    "css",
    "html",
    "javascript",
    "js",
    "json",
    "jsx",
    "python",
    "sql",
    "ts",
    "tsx",
    "typescript",
}


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


def _code_blocks(text: str, language: str = "plain text") -> list[dict]:
    return [
        {
            "object": "block",
            "type": "code",
            "code": {"rich_text": _plain_text_chunks(chunk), "language": language},
        }
        for chunk in _split_text(text)
    ] or [_text_block("paragraph", " ")]


def _markdown_blocks(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False
    code_lang = ""

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        blocks.append(_text_block("paragraph", "\n".join(paragraph_lines).strip()))
        paragraph_lines.clear()

    def flush_code() -> None:
        if not code_lines:
            return
        code_text = "\n".join(code_lines).rstrip()
        if _looks_like_code(code_text, code_lang):
            blocks.extend(_code_blocks(code_text, _notion_code_language(code_lang)))
        else:
            blocks.append(_text_block("paragraph", _plainify_diagram(code_text)))
        code_lines.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        fence = re.match(r"^```([A-Za-z0-9_-]+)?", stripped)
        if fence:
            if in_code:
                flush_code()
                in_code = False
                code_lang = ""
            else:
                flush_paragraph()
                in_code = True
                code_lang = fence.group(1) or ""
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

        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            blocks.append(_text_block("bulleted_list_item", _clean_list_text(bullet.group(1))))
            continue

        numbered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if numbered:
            flush_paragraph()
            blocks.append(_text_block("numbered_list_item", _clean_list_text(numbered.group(1))))
            continue

        paragraph_lines.append(stripped)

    if in_code:
        flush_code()
    flush_paragraph()
    return blocks or [_text_block("paragraph", "No content.")]


def clean_notion_title(prefix: str, topic: str, max_length: int = 90) -> str:
    title = re.sub(r"\s+", " ", topic).strip(" -_\t\n")
    title = re.sub(r"\brun_[A-Za-z0-9_,-]+\b", "", title).strip(" -_,")
    title = title[:max_length].rstrip(" -_,")
    if not title:
        title = "Research run"
    return f"{prefix}{title}"[:100].rstrip(" -_,")


def _clean_list_text(text: str) -> str:
    cleaned = text.strip()
    while re.match(r"^\d+\.\s+", cleaned):
        cleaned = re.sub(r"^\d+\.\s+", "", cleaned, count=1)
    return cleaned or text.strip()


def _looks_like_code(text: str, language: str) -> bool:
    if language.lower() in {"text", "plain", "plaintext"}:
        return False
    if language.lower() in CODE_LANGS:
        return True
    code_markers = ["const ", "let ", "function ", "=>", "import ", "def ", "{", "}", "</", "SELECT "]
    return any(marker in text for marker in code_markers)


def _notion_code_language(language: str) -> str:
    lower = language.lower()
    if lower in {"js", "jsx"}:
        return "javascript"
    if lower in {"ts", "tsx"}:
        return "typescript"
    if lower in CODE_LANGS:
        return "plain text" if lower == "text" else lower
    return "plain text"


def _plainify_diagram(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


@dataclass
class NotionClient:
    api_key: str | None
    prompts_database_id: str | None
    responses_database_id: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.prompts_database_id and self.responses_database_id)

    async def save_prompt(
        self,
        run_id: str,
        intake: ResearchIntake,
        memory_context: MemoryContext | None = None,
    ) -> str | None:
        if not self.enabled:
            return None
        title = clean_notion_title("Prompt: ", intake.niche_research_topic)
        body = _notion_run_metadata(run_id, memory_context) + "\n\n" + intake.model_dump_json(by_alias=True, indent=2)
        return await self._create_page(self.prompts_database_id, title, body)

    async def save_response(
        self,
        run_id: str,
        intake: ResearchIntake,
        markdown: str,
        memory_context: MemoryContext | None = None,
    ) -> str | None:
        if not self.enabled:
            return None
        title = clean_notion_title("Response: ", intake.niche_research_topic)
        body = markdown.rstrip() + "\n\n# Run metadata\n\n" + _notion_run_metadata(run_id, memory_context)
        return await self._create_page(self.responses_database_id, title, body)

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


def _notion_run_metadata(run_id: str, memory_context: MemoryContext | None) -> str:
    if not memory_context:
        return f"Run ID: {run_id}\nMemory context: not loaded yet."
    return "\n".join(
        [
            f"Run ID: {run_id}",
            f"Workflow version: {memory_context.workflow_version}",
            f"Instruction version: {memory_context.instruction_version}",
            f"Source policy version: {memory_context.source_policy_version}",
            f"Notion formatting version: {memory_context.notion_formatting_version}",
            f"Learning output version: {memory_context.learning_output_version}",
        ]
    )
