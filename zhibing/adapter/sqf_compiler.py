"""Compile validated TaskSubmitRequest JSON into a controlled SQF call plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from zhibing.core.coord_service import CoordService, default_coord_service


class SQFCompileError(ValueError):
    """Raised when structured JSON cannot be safely compiled to SQF."""


@dataclass(frozen=True)
class SQFCallPlan:
    task_id: str
    statements: tuple[str, ...]


class SQFCompiler:
    """Deterministic JSON to SQF compiler.

    This is the only place where VBS-native SQF syntax is emitted. The LLM layer
    never writes SQF and cannot inject script fragments because all values are
    encoded by type.
    """

    def __init__(self, coord_service: CoordService | None = None) -> None:
        self.coord_service = coord_service or default_coord_service

    def compile_submit(self, request: Mapping[str, Any], *, task_id: str) -> SQFCallPlan:
        actor = request["actor"]
        task = request["task"]
        actor_expr = self._actor_expr(actor)
        btset_path = self._quote(str(task["btset_path"]))
        bt_name = self._quote(str(task["bt_name"]))
        scope = self._quote(str(task["bt_scope"]))
        statements = [
            f'_status = loadBTSet {btset_path};',
            f'{actor_expr} setBT [{bt_name}, {scope}];',
        ]
        for key, value in task["bt_args"].items():
            encoded = self._sqf_value(value)
            statements.append(f'{actor_expr} setBBVariable [{self._quote(key)}, {encoded}];')
        statements.append(f'{actor_expr} receiveMessage ["DoNewTaskRequest", ["task_id", {self._quote(task_id)}]];')
        return SQFCallPlan(task_id=task_id, statements=tuple(statements))

    def _actor_expr(self, actor: Mapping[str, str]) -> str:
        actor_id = actor["id"]
        if not actor_id.replace("_", "").isalnum():
            raise SQFCompileError("actor id contains unsupported characters.")
        if actor["type"] == "group":
            return f"(group {actor_id})"
        if actor["type"] == "soldier":
            return actor_id
        raise SQFCompileError("actor type must be group or soldier.")

    def _sqf_value(self, value: Any) -> str:
        if isinstance(value, Mapping) and "frame" in value:
            local = self.coord_service.to_vbs_local(value)
            left = chr(91)
            right = chr(93)
            return f"{left}{float(local['x']):.6f}, {float(local['y']):.6f}, {float(local['z']):.6f}{right}"
        if isinstance(value, str):
            return self._quote(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(float(value))
        if isinstance(value, Mapping):
            items = []
            for key, item in value.items():
                items.append(self._sqf_value(str(key)))
                items.append(self._sqf_value(item))
            return self._sqf_sequence(items)
        if isinstance(value, (list, tuple)):
            return self._sqf_sequence([self._sqf_value(item) for item in value])
        if value is None:
            return "nil"
        raise SQFCompileError(f"Unsupported SQF value type: {type(value).__name__}")

    def _sqf_sequence(self, encoded_items: list[str]) -> str:
        left = chr(91)
        right = chr(93)
        return f"{left}{', '.join(encoded_items)}{right}"

    def _quote(self, value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

