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
        if not self.enabled:
            return None
        import boto3

        today = datetime.now(timezone.utc)
        key = f"run-summaries/{today:%Y/%m/%d}/{run_id}.json"
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
            Body=json.dumps(summary, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        return key
