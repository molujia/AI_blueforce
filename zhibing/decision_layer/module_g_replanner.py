"""Module G: MVP replan trigger for recoverable failures."""

from __future__ import annotations

from typing import Any

from zhibing.core.db import InMemoryRepository
from zhibing.scene import scene_tools


def replan_after_failure(repository: InMemoryRepository, *, task_id: str, status_response: dict[str, Any]) -> dict[str, Any]:
    """Run SECTION 11 steps 1-2 enough to prove the upper layer can diagnose."""

    task = repository.task_instances[task_id]
    actor_state = scene_tools.get_actor_state(task["actor_id"])
    error = status_response.get("error") or {}
    obstacle = scene_tools.query_obstacle(error.get("blocked_segment", ""))
    snapshot = {"actor_state": actor_state, "obstacle": obstacle, "status_response": status_response}
    repository.snapshot_scene(task_id=task_id, snapshot_data=snapshot)
    diagnosis = "ROUTE_BLOCKED" if status_response.get("return_code") == "UNREACHABLE" and not obstacle.get("passable", True) else "UNKNOWN"
    event = {"task_id": task_id, "replan_attempted": True, "diagnosis": diagnosis, "new_task_submitted": False}
    if diagnosis == "ROUTE_BLOCKED":
        event["suggested_action"] = "REQUEST_HUMAN" if not obstacle.get("passable", True) else "REPLAN_ROUTE"
    return event

