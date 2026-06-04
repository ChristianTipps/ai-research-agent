from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


def load_environment() -> None:
    """Load local env files for development without affecting production env vars."""
    roots = [
        Path.cwd(),
        Path(__file__).resolve().parents[4],
        Path(__file__).resolve().parents[2],
    ]
    for root in roots:
        for name in (".env.local", ".env"):
            candidate = root / name
            if candidate.exists():
                load_dotenv(candidate, override=False)


class Settings(BaseModel):
    openai_api_key: str | None
    openai_model: str
    enable_openai_web_search: bool

    database_url: str | None
    local_sqlite_path: str

    agent_backend_token: str | None

    notion_api_key: str | None
    notion_prompts_database_id: str | None
    notion_responses_database_id: str | None

    do_spaces_region: str
    do_spaces_bucket: str
    do_spaces_endpoint: str
    do_spaces_access_key_id: str | None
    do_spaces_secret_access_key: str | None


def get_settings() -> Settings:
    load_environment()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
        enable_openai_web_search=os.getenv("ENABLE_OPENAI_WEB_SEARCH", "true").lower()
        in {"1", "true", "yes"},
        database_url=os.getenv("DATABASE_URL"),
        local_sqlite_path=os.getenv("LOCAL_SQLITE_PATH", "./data/local.db"),
        agent_backend_token=os.getenv("AGENT_BACKEND_TOKEN"),
        notion_api_key=os.getenv("NOTION_API_KEY"),
        notion_prompts_database_id=os.getenv("NOTION_PROMPTS_DATABASE_ID"),
        notion_responses_database_id=os.getenv("NOTION_RESPONSES_DATABASE_ID"),
        do_spaces_region=os.getenv("DO_SPACES_REGION", "sfo3"),
        do_spaces_bucket=os.getenv("DO_SPACES_BUCKET", "ai-research-agent-kb-a01bd200"),
        do_spaces_endpoint=os.getenv(
            "DO_SPACES_ENDPOINT", "https://sfo3.digitaloceanspaces.com"
        ),
        do_spaces_access_key_id=os.getenv("DO_SPACES_ACCESS_KEY_ID"),
        do_spaces_secret_access_key=os.getenv("DO_SPACES_SECRET_ACCESS_KEY"),
    )
