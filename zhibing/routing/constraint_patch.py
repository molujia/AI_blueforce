"""Structured route-planning constraint patches produced by LLM parsing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ConstraintPatch:
    constraint_id: str
    source_text: str
    action: Literal["avoid", "ignore_zone", "prefer", "priority"]
    target_type: Literal["road_class", "enemy_zone", "risk_zone", "route_metric"]
    target_id: str
    weight_delta: float
    reason: str
    priority: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

