"""Database-facing models plus an in-memory MVP repository.

The production target is PostgreSQL + PostGIS. The MVP repository keeps tests
and offline demos runnable while preserving transaction-shaped write methods.
"""

from __future__ import annotations

import copy
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InMemoryRepository:
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    mission_plans: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_instances: dict[str, dict[str, Any]] = field(default_factory=dict)
    vbs_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    vbs_returns: dict[str, dict[str, Any]] = field(default_factory=dict)
    scene_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    decision_logs: dict[str, dict[str, Any]] = field(default_factory=dict)
    entity_states: dict[str, dict[str, Any]] = field(default_factory=dict)

    @contextmanager
    def transaction(self) -> Iterator["InMemoryRepository"]:
        backup = copy.deepcopy(self.__dict__)
        try:
            yield self
        except Exception:
            self.__dict__.update(backup)
            raise

    def create_session(self, *, user_id: str, scenario_id: str) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "scenario_id": scenario_id,
            "created_at": utc_now_iso(),
            "status": "active",
        }
        return session_id

    def create_mission_plan(self, *, session_id: str, user_intent: str, plan_json: dict[str, Any]) -> str:
        mission_id = str(uuid.uuid4())
        self.mission_plans[mission_id] = {
            "mission_id": mission_id,
            "session_id": session_id,
            "user_intent": user_intent,
            "plan_json": plan_json,
            "created_at": utc_now_iso(),
        }
        return mission_id

    def create_task_instance(self, *, mission_id: str, session_id: str, step: dict[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        actor = step["actor"]
        self.task_instances[task_id] = {
            "task_id": task_id,
            "mission_id": mission_id,
            "session_id": session_id,
            "step_id": step["step_id"],
            "actor_type": actor["type"],
            "actor_id": actor["id"],
            "bt_name": step["bt"]["bt_name"],
            "bt_args": step["args"],
            "state": "CREATED",
            "timeout_policy": step["timeout_policy"],
            "created_at": utc_now_iso(),
        }
        return task_id

    def update_task_state(self, task_id: str, state: str, **extra: Any) -> None:
        self.task_instances[task_id]["state"] = state
        self.task_instances[task_id]["last_status_at"] = utc_now_iso()
        self.task_instances[task_id].update(extra)

    def log_vbs_request(self, *, task_id: str, request_type: str, payload: dict[str, Any]) -> str:
        request_id = payload.get("request_id") or str(uuid.uuid4())
        self.vbs_requests[request_id] = {
            "request_id": request_id,
            "task_id": task_id,
            "request_type": request_type,
            "payload": payload,
            "sent_at": utc_now_iso(),
        }
        return request_id

    def log_vbs_return(self, *, request_id: str, task_id: str, payload: dict[str, Any]) -> str:
        return_id = str(uuid.uuid4())
        self.vbs_returns[return_id] = {
            "return_id": return_id,
            "request_id": request_id,
            "task_id": task_id,
            "payload": payload,
            "received_at": utc_now_iso(),
        }
        return return_id

    def write_decision_log(self, entry: dict[str, Any]) -> str:
        decision_id = entry.get("decision_id") or str(uuid.uuid4())
        payload = dict(entry)
        payload["decision_id"] = decision_id
        payload.setdefault("created_at", utc_now_iso())
        self.decision_logs[decision_id] = payload
        return decision_id

    def snapshot_scene(self, *, task_id: str, snapshot_data: dict[str, Any]) -> str:
        snapshot_id = str(uuid.uuid4())
        self.scene_snapshots[snapshot_id] = {
            "snapshot_id": snapshot_id,
            "task_id": task_id,
            "snapshot_data": snapshot_data,
            "captured_at": utc_now_iso(),
        }
        return snapshot_id

