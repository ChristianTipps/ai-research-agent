from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from botocore.exceptions import ClientError


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
        return self.save_text(key, markdown, "text/markdown; charset=utf-8")

    def save_text(self, key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str | None:
        if not self.enabled:
            return None
        self._put_object(key, text.encode("utf-8"), content_type)
        return key

    def get_text(self, key: str) -> str | None:
        if not self.enabled:
            return None
        try:
            response = self._client().get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                return None
            raise

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        text = self.get_text(key)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def object_exists(self, key: str) -> bool:
        if not self.enabled:
            return False
        try:
            self._client().head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
                return False
            raise

    def list_keys(self, prefix: str, *, limit: int = 100) -> list[str]:
        if not self.enabled:
            return []
        response = self._client().list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix,
            MaxKeys=limit,
        )
        return [item["Key"] for item in response.get("Contents", [])]

    def _put_object(self, key: str, body: bytes, content_type: str) -> None:
        self._client().put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    def _client(self):
        import boto3

        return boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )


def dated_artifact_key(prefix: str, run_id: str, name: str, extension: str) -> str:
    return _dated_key(prefix, run_id, name, extension)


def _dated_key(prefix: str, run_id: str, name: str, extension: str) -> str:
    today = datetime.now(timezone.utc)
    safe_name = "".join(char if char.isalnum() or char in "-_" else "-" for char in name.lower())
    safe_name = "-".join(part for part in safe_name.split("-") if part)
    return f"{prefix}/{today:%Y/%m/%d}/{run_id}/{safe_name}.{extension}"
