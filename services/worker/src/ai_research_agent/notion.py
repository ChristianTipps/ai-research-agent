from __future__ import annotations

from dataclasses import dataclass

import httpx

from .schemas import ResearchIntake


def _rich_text_chunks(markdown: str) -> list[dict]:
    chunks: list[dict] = []
    for start in range(0, len(markdown), 1800):
        chunks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": markdown[start : start + 1800]},
                        }
                    ]
                },
            }
        )
    return chunks or [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "No content."}}]},
        }
    ]


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
            "children": _rich_text_chunks(markdown),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.notion.com/v1/pages", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("url") or data.get("id")
