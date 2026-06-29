"""Configurable HITL guard definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zhibing.hitl.node_catalog import NodeType

try:  # pragma: no cover - optional dependency path
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class HITLInterrupt:
    trigger: str
    actor: dict[str, str]
    proposed_action: dict[str, Any]
    risk_assessment: str
    decision_options: tuple[str, str, str] = ("approve", "modify", "abort")


@dataclass(frozen=True)
class HITLDecisionContext:
    node_type: NodeType
    urgency: str
    trigger: str
    actor: dict[str, str]
    proposed_action: dict[str, Any]
    risk_assessment: str


class HITLPolicy:
    def __init__(self, nodes: dict[str, dict[str, Any]]) -> None:
        self.nodes = nodes

    @classmethod
    def default(cls) -> "HITLPolicy":
        path = Path(__file__).with_name("hitl_policy.yaml")
        if not path.exists():
            return cls.from_dict({})
        return cls.from_dict(_load_policy_file(path))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HITLPolicy":
        return cls(nodes=dict(data.get("nodes") or {}))

    def evaluate(self, context: HITLDecisionContext) -> HITLInterrupt | None:
        cfg = self.nodes.get(context.node_type.value, {})
        if context.urgency == "immediate" and cfg.get("allow_emergency_skip", True):
            return None
        if not cfg.get("hitl_allowed", False):
            return None
        if not cfg.get("require_hitl", False):
            return None
        return HITLInterrupt(
            trigger=context.trigger,
            actor=context.actor,
            proposed_action=context.proposed_action,
            risk_assessment=context.risk_assessment,
        )


def check_hitl_required(intent_json: dict[str, Any], policy: HITLPolicy | None = None) -> HITLInterrupt | None:
    task_type = str(intent_json.get("intent", "")).lower()
    actor = (intent_json.get("actors") or [{"type": "group", "id": "p_4"}])[0]
    if "fire" in task_type or "attack" in task_type:
        context = HITLDecisionContext(
            node_type=NodeType.FIRE_OR_ATTACK_AUTHORIZATION,
            urgency="normal",
            trigger="CONFIGURED_HITL_NODE",
            actor=actor,
            proposed_action=intent_json,
            risk_assessment="Kinetic action requires configured human authorization.",
        )
        return (policy or HITLPolicy.default()).evaluate(context)
    if "encircle" in task_type or "encirclement" in task_type:
        context = HITLDecisionContext(
            node_type=NodeType.ENCIRCLEMENT_PREP_CHECK,
            urgency="normal",
            trigger="CONFIGURED_HITL_NODE",
            actor=actor,
            proposed_action=intent_json,
            risk_assessment="Encirclement preparation gate configured by policy.",
        )
        return (policy or HITLPolicy.default()).evaluate(context)
    return None


def _load_policy_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if yaml is not None:
        data = yaml.safe_load(text)
        return data or {}
    return _parse_simple_hitl_yaml(text)


def _parse_simple_hitl_yaml(text: str) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "nodes:":
            continue
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            current = stripped[:-1]
            nodes[current] = {}
            continue
        if current and line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            value = value.strip()
            if value.lower() == "true":
                parsed: Any = True
            elif value.lower() == "false":
                parsed = False
            else:
                parsed = value
            nodes[current][key.strip()] = parsed
    return {"nodes": nodes}
