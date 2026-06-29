"""Typed structures for BattlefieldProjection dictionaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectionUnit:
    id: str
    type: str
    status: str
    position: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProjectionRoute:
    id: str
    task_type: str
    bt_name: str
    waypoints: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ProjectionTarget:
    id: str
    kind: str
    coord: dict[str, Any]


@dataclass(frozen=True)
class BattlefieldProjection:
    mission_id: str
    intent: str | None
    units: list[ProjectionUnit] = field(default_factory=list)
    routes: list[ProjectionRoute] = field(default_factory=list)
    targets: list[ProjectionTarget] = field(default_factory=list)
    zones: list[dict[str, Any]] = field(default_factory=list)
    pending_intents: list[dict[str, Any]] = field(default_factory=list)
    task_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "intent": self.intent,
            "units": [unit.__dict__ for unit in self.units],
            "routes": [{**route.__dict__, "waypoints": list(route.waypoints)} for route in self.routes],
            "targets": [target.__dict__ for target in self.targets],
            "zones": self.zones,
            "pending_intents": self.pending_intents,
            "task_state": self.task_state,
        }