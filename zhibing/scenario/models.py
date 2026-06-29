"""Scenario data structures for the v0 Zhibing demonstration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Coordinate = dict[str, float | str]


@dataclass(frozen=True)
class BattlefieldUnit:
    id: str
    name: str
    side: Literal["friendly", "enemy"]
    kind: str
    position: Coordinate
    radius_m: float = 20.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskZone:
    id: str
    name: str
    kind: Literal["enemy_fire", "sniper_risk", "generic_risk"]
    center: Coordinate
    radius_m: float
    weight: float
    source: str = "scenario"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TargetPoint:
    id: str
    name: str
    kind: Literal["building_entry", "point"]
    position: Coordinate

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteCandidate:
    id: str
    waypoints: list[Coordinate]
    distance_m: float
    risk_score: float
    time_score: float
    total_score: float
    labels: list[str] = field(default_factory=list)
    constraint_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

