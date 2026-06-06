from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class SpacesClient:
    bucket: str
    region: str
    endpoint: str
    access_key_id: str | None
    secret_access_key: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.bucket and self.access_key_id and self.secret_access_key)

    def save_run_summary(self, run_id: str, summary: dict[str, Any]) -> str | None:
        return self.save_json(
            _dated_key("run-summaries", run_id, "summary", "json"),
            summary,
        )

    def save_json(self, key: str, payload: dict[str, Any] | list[Any]) -> str | None:
        if not self.enabled:
            return None
        self._put_object(
            key,
            json.dumps(payload, indent=2, default=str).encode("utf-8"),
            "application/json",
        )
        return key

    def save_markdown(self, key: str, markdown: str) -> str | None:
        if not self.enabled:
            return None
        self._put_object(key, markdown.encode("utf-8"), "text/markdown; charset=utf-8")
        return key

    def _put_object(self, key: str, body: bytes, content_type: str) -> None:
        import boto3

        client = boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )


def dated_artifact_key(prefix: str, run_id: str, name: str, extension: str) -> str:
    return _dated_key(prefix, run_id, name, extension)


def _dated_key(prefix: str, run_id: str, name: str, extension: str) -> str:
    today = datetime.now(timezone.utc)
    safe_name = "".join(char if char.isalnum() or char in "-_" else "-" for char in name.lower())
    safe_name = "-".join(part for part in safe_name.split("-") if part)
    return f"{prefix}/{today:%Y/%m/%d}/{run_id}/{safe_name}.{extension}"
