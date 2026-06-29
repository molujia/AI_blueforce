"""Module D: BT selection from the registry."""

from __future__ import annotations

from typing import Any


class BTSelectionError(RuntimeError):
    """Raised when no registry entry can satisfy the intent."""


def select_bt(intent_json: dict[str, Any], scene_context: dict[str, Any]) -> tuple[dict[str, Any], str, list[dict[str, str]]]:
    candidates = scene_context.get("bt_candidates") or []
    if not candidates:
        raise BTSelectionError("No active BT registry entry matches this intent and actor scope.")
    selected = candidates[0]
    rejected = [
        {"bt_name": item["bt_name"], "rejected_reason": "lower capability score or less direct MVP fit"}
        for item in candidates[1:]
    ]
    reason = f"Selected {selected['bt_name']} because it matches {intent_json['intent']} for actor scope {selected['scope']}."
    return selected, reason, rejected

