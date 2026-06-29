"""HTTP transport for the lower simulation wrapper."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from zhibing.adapter.sqf_compiler import SQFCallPlan


class LowerSimHTTPTransport:
    def __init__(self, base_url: str, timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_submit_payload(self, *, task_id: str, request: dict[str, Any], sqf_statements: tuple[str, ...]) -> dict[str, Any]:
        return {"task_id": task_id, "request": request, "sqf_statements": list(sqf_statements)}

    def submit_sqf_plan(self, plan: SQFCallPlan, request: dict[str, Any]) -> dict[str, Any]:
        payload = self.build_submit_payload(task_id=plan.task_id, request=request, sqf_statements=plan.statements)
        return self._post_json("/tasks/submit", payload)

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        return self._post_json("/tasks/query", {"task_id": task_id, "query_fields": query_fields or []})

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))