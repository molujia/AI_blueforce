"""Layer 3 VBS adapter and replaceable lower-layer transport."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from zhibing.adapter.sqf_compiler import SQFCallPlan, SQFCompiler
from zhibing.core.coord_service import default_coord_service


LOAD_ERROR_CODES = {"BT_LOAD_ERROR", "BT_NOT_FOUND", "ACTOR_NOT_FOUND", "PARAM_ERROR"}
EXECUTION_FAILURE_CODES = {"UNREACHABLE", "SUBTASK_FAILED", "TARGET_LOST", "UNIT_STATUS_CHANGED"}


class VbsTransport(Protocol):
    """Required lower-layer boundary for HTTP, socket, or in-process VBS return data."""

    def submit_sqf_plan(self, plan: SQFCallPlan, request: dict[str, Any]) -> dict[str, Any]:
        """Return an ACK or classified load error from the VBS wrapper."""

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        """Return task runtime status, progress, active node, and return code."""


@dataclass
class MockVbsTransport:
    """Offline VBS simulator for MVP acceptance tests."""

    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)

    def submit_sqf_plan(self, plan: SQFCallPlan, request: dict[str, Any]) -> dict[str, Any]:
        actor_id = request["actor"]["id"]
        if actor_id.startswith("missing"):
            return {"ok": False, "return_code": "ACTOR_NOT_FOUND", "message": "actor not present in scenario"}
        bt_name = request["task"]["bt_name"]
        if bt_name == "unknown":
            return {"ok": False, "return_code": "BT_NOT_FOUND", "message": "behavior tree not registered"}
        args = request["task"]["bt_args"]
        destination = args.get("movePos") or args.get("moveDest")
        passable = True
        blocked_segment = None
        if isinstance(destination, dict):
            local = default_coord_service.to_vbs_local(destination)
            if float(local["x"]) >= 9000:
                passable = False
                blocked_segment = "mock_blocked_corridor"
        self.tasks[plan.task_id] = {
            "request": request,
            "query_count": 0,
            "passable": passable,
            "blocked_segment": blocked_segment,
            "sqf": plan.statements,
        }
        return {"ok": True, "status": "ACKED", "task_id": plan.task_id, "message": "BT loaded"}

    def query_task(self, task_id: str, query_fields: list[str] | None = None) -> dict[str, Any]:
        task = self.tasks[task_id]
        task["query_count"] += 1
        request = task["request"]
        args = request["task"]["bt_args"]
        destination = args.get("movePos") or args.get("moveDest") or {"frame": "VBS_LOCAL_XYZ", "x": 0.0, "y": 0.0, "z": 0.0}
        local = default_coord_service.to_vbs_local(destination)
        elapsed = float(task["query_count"] * 10)
        if not task["passable"]:
            return {
                "session_id": request["session_id"],
                "task_id": task_id,
                "status": "FAILED",
                "actor": {"type": request["actor"]["type"], "id": request["actor"]["id"], "position": local},
                "bt_runtime": {"bt_name": request["task"]["bt_name"], "active_node": "move", "node_path": ["main thread", "move"]},
                "progress": {"distance_to_goal_m": 0.0, "elapsed_seconds": elapsed, "estimated_remaining_seconds": 0.0, "progress_rate_mps": 0.0},
                "return_code": "UNREACHABLE",
                "error": {"class": "EXECUTION", "message": "mock route is blocked", "position": local, "blocked_segment": task["blocked_segment"]},
                "suggested_action": "REPLAN_ROUTE",
            }
        return {
            "session_id": request["session_id"],
            "task_id": task_id,
            "status": "SUCCEEDED",
            "actor": {"type": request["actor"]["type"], "id": request["actor"]["id"], "position": local},
            "bt_runtime": {"bt_name": request["task"]["bt_name"], "active_node": "end", "node_path": ["main thread", "move", "end"]},
            "progress": {"distance_to_goal_m": 0.0, "elapsed_seconds": elapsed, "estimated_remaining_seconds": 0.0, "progress_rate_mps": float(args.get("speed", 1.0))},
            "return_code": "SUCCESS",
            "error": None,
            "suggested_action": None,
        }


class VBSAdapter:
    """Layer 3 adapter that accepts JSON requests and emits JSON responses."""

    def __init__(self, transport: VbsTransport | None = None, compiler: SQFCompiler | None = None) -> None:
        self.transport = transport or MockVbsTransport()
        self.compiler = compiler or SQFCompiler()

    @classmethod
    def from_config(cls) -> "VBSAdapter":
        from zhibing.config import LOWER_SIM_HTTP_BASE_URL, LOWER_SIM_SOCKET_HOST, LOWER_SIM_SOCKET_PORT, LOWER_SIM_TRANSPORT

        if LOWER_SIM_TRANSPORT == "http":
            from zhibing.adapter.http_transport import LowerSimHTTPTransport

            return cls(transport=LowerSimHTTPTransport(LOWER_SIM_HTTP_BASE_URL))
        if LOWER_SIM_TRANSPORT == "socket":
            from zhibing.adapter.socket_transport import LowerSimSocketTransport

            return cls(transport=LowerSimSocketTransport(LOWER_SIM_SOCKET_HOST, LOWER_SIM_SOCKET_PORT))
        if LOWER_SIM_TRANSPORT == "mock":
            return cls(transport=MockVbsTransport())
        raise ValueError(f"Unsupported lower simulation transport: {LOWER_SIM_TRANSPORT}")

    def load_btset(self, btset_path: str) -> dict[str, Any]:
        return {"ok": bool(btset_path), "return_code": None if btset_path else "BT_LOAD_ERROR"}

    def set_bt(self, actor: dict[str, str], bt_name: str, scope: str) -> dict[str, Any]:
        return {"ok": bool(actor and bt_name and scope), "return_code": None}

    def set_bb_variable(self, actor: dict[str, str], name: str, value: Any) -> dict[str, Any]:
        return {"ok": name != "", "return_code": None, "value": value}

    def send_message(self, actor: dict[str, str], subject: str, value: dict[str, Any]) -> dict[str, Any]:
        return {"ok": subject != "", "return_code": None, "value": value}

    def submit_task(self, request: dict[str, Any], *, task_id: str | None = None) -> dict[str, Any]:
        task_id = task_id or str(uuid.uuid4())
        plan = self.compiler.compile_submit(request, task_id=task_id)
        raw = self.transport.submit_sqf_plan(plan, request)
        if not raw.get("ok"):
            return {
                "session_id": request["session_id"],
                "task_id": task_id,
                "status": "FAILED",
                "return_code": self.classify_return(raw),
                "error": {"class": "LOAD", "message": raw.get("message", "load error")},
                "compiled_sqf": plan.statements,
            }
        return {
            "session_id": request["session_id"],
            "task_id": task_id,
            "status": "ACKED",
            "return_code": None,
            "compiled_sqf": plan.statements,
        }

    def query_status(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.transport.query_task(request["task_id"], request.get("query_fields"))

    def classify_return(self, raw: dict[str, Any]) -> str:
        code = str(raw.get("return_code") or raw.get("code") or "")
        if code in LOAD_ERROR_CODES or code in EXECUTION_FAILURE_CODES or code in {"SUCCESS", "WAIT_UPPER", "TIMEOUT"}:
            return code
        text = f"{raw.get('message', '')} {raw.get('error', '')}".lower()
        if "actor" in text and "not" in text:
            return "ACTOR_NOT_FOUND"
        if "bt" in text and "load" in text:
            return "BT_LOAD_ERROR"
        if "param" in text:
            return "PARAM_ERROR"
        return "BT_LOAD_ERROR"