"""Module H: explainability logging and query."""

from __future__ import annotations

import uuid
from typing import Any

from zhibing.core.db import InMemoryRepository, utc_now_iso


class ExplainabilityLogger:
    def __init__(self, repository: InMemoryRepository) -> None:
        self.repository = repository

    def log_bt_selection(
        self,
        *,
        session_id: str,
        task_id: str,
        user_intent: str,
        intent_json: dict[str, Any],
        selected_bt: dict[str, Any],
        selection_reason: str,
        alternatives_considered: list[dict[str, str]],
        parameters_sourced: dict[str, Any],
        coord_conversions: list[dict[str, Any]] | None = None,
    ) -> str:
        entry = {
            "decision_id": str(uuid.uuid4()),
            "session_id": session_id,
            "task_id": task_id,
            "user_intent": user_intent,
            "intent_json": intent_json,
            "selected_bt": selected_bt["bt_name"],
            "selection_reason": selection_reason,
            "alternatives_considered": alternatives_considered,
            "parameters_sourced": parameters_sourced,
            "bt_node_trace": selected_bt.get("explainable_nodes", []),
            "coord_conversions": coord_conversions or [],
            "timestamp": utc_now_iso(),
        }
        return self.repository.write_decision_log(entry)

    def explain_task(self, task_id: str) -> str:
        logs = [entry for entry in self.repository.decision_logs.values() if entry["task_id"] == task_id]
        if not logs:
            return "No decision log found for this task."
        log = logs[-1]
        return (
            f"Task {task_id} selected {log['selected_bt']}. "
            f"Reason: {log['selection_reason']} "
            f"Parameters: {', '.join(log['parameters_sourced'].keys())}."
        )

