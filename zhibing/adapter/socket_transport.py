"""Socket transport for the lower simulation wrapper."""

from __future__ import annotations

import json
import socket
import uuid
from typing import Any

from zhibing.adapter.sqf_compiler import SQFCallPlan


class LowerSimSocketTransport:
    def __init__(self, host: str, port: int, timeout_seconds: float = 20.0) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds

    def build_envelope(self, message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"message_id": str(uuid.uuid4()), "message_type": message_type, "payload": payload}

    def submit_sqf_plan(self, plan: SQFCallPlan, request: dict[str, Any]) -> dict[str, Any]:
        payload = {"task_id": plan.task_id, "request": request, "sqf_statements": list(plan.statements)}
        return self._send(self.build_envelope("TASK_SUBMIT", payload))

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        return self._send(self.build_envelope("TASK_QUERY", {"task_id": task_id, "query_fields": query_fields or []}))

    def _send(self, envelope: dict[str, Any]) -> dict[str, Any]:
        data = (json.dumps(envelope, ensure_ascii=False) + "\n").encode("utf-8")
        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as conn:
            conn.sendall(data)
            response = conn.recv(1024 * 1024)
        return json.loads(response.decode("utf-8"))