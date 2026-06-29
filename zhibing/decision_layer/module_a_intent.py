"""Module A: intent recognition with LLM-first, deterministic-fallback parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from zhibing.config import LLM_CONFIG_FILE, SCHEMA_DIR
from zhibing.core.coord_service import default_coord_service

try:
    from llm_migration_client import call_json_agent, load_llm_config
except Exception:  # pragma: no cover - optional online dependency
    call_json_agent = None
    load_llm_config = None


def recognize_intent(user_text: str, *, prefer_llm: bool = True) -> dict[str, Any]:
    """Return IntentJSON. LLM output is schema-prompted; fallback is regex-based."""

    if prefer_llm and call_json_agent and load_llm_config:
        config = load_llm_config(LLM_CONFIG_FILE)
        if config.api_key or config.base_url:
            try:
                parsed, _thoughts, _cleaned = call_json_agent(_messages(user_text), config=config, max_tokens=1000)
                return _normalize_intent(parsed)
            except Exception:
                pass
    return _fallback_intent(user_text)


def _messages(user_text: str) -> list[dict[str, str]]:
    schema = Path(SCHEMA_DIR / "intent_json.schema.json").read_text(encoding="utf-8")
    system = (
        "You are Module A of Zhibing. Return only one JSON object matching IntentJSON. "
        "Never emit SQF, scripts, or markdown. Complex tactical tasks must still be JSON only. "
        f"Schema appendix follows:\n{schema}\n"
        "Few-shot move: user=order p_4 group speed 10 move to VBS_LOCAL_XYZ {x:1000, y:500, z:0}; "
        "json={\"intent\":\"group_move\",\"actors\":[{\"type\":\"group\",\"id\":\"p_4\"}],"
        "\"destination\":{\"type\":\"absolute\",\"coord\":{\"frame\":\"VBS_LOCAL_XYZ\",\"x\":1000,\"y\":500,\"z\":0}},"
        "\"movement_mode\":\"normal\",\"constraints\":{\"avoid_enemy\":false,\"maintain_formation\":true,\"allow_replan\":true}}\n"
        "Few-shot encirclement: user=order p_4 encircle target building entry VBS_LOCAL_XYZ {x:1000,y:500,z:0}; "
        "json={\"intent\":\"encircle_building\",\"actors\":[{\"type\":\"group\",\"id\":\"p_4\"}],"
        "\"destination\":{\"type\":\"absolute\",\"coord\":{\"frame\":\"VBS_LOCAL_XYZ\",\"x\":1000,\"y\":500,\"z\":0}},"
        "\"target\":{\"type\":\"building\"},\"movement_mode\":\"normal\","
        "\"constraints\":{\"avoid_enemy\":true,\"maintain_formation\":true,\"allow_replan\":true}}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user_text}]


def _fallback_intent(user_text: str) -> dict[str, Any]:
    actor_match = re.search(r"\b([A-Za-z]+_\w+)\b", user_text)
    actor_id = actor_match.group(1) if actor_match else "p_4"
    is_encirclement = _is_encirclement_command(user_text)
    actor_type = "group" if is_encirclement or "群组" in user_text or actor_id.startswith(("p_", "grp")) else "soldier"
    coord = _extract_coord(user_text)
    speed_match = re.search(r"(?:速度|speed)\s*[:=]?\s*(\d+(?:\.\d+)?)", user_text, re.I)
    movement_mode = "urgent" if "紧急" in user_text or "urgent" in user_text.lower() else "normal"
    intent_name = "encircle_building" if is_encirclement else ("group_move" if actor_type == "group" else "soldier_move")
    intent: dict[str, Any] = {
        "intent": intent_name,
        "actors": [{"type": actor_type, "id": actor_id}],
        "destination": {"type": "absolute", "coord": coord},
        "movement_mode": movement_mode,
        "constraints": {
            "avoid_enemy": is_encirclement or "避敌" in user_text or "avoid_enemy" in user_text or "enemy" in user_text.lower(),
            "maintain_formation": True,
            "allow_replan": True,
        },
    }
    if is_encirclement:
        intent["target"] = {"type": "building", "entry_coord": coord}
        intent["knowledge_query"] = "encirclement building entry enemy fire route assessment"
    if speed_match:
        intent["speed_mps"] = float(speed_match.group(1))
    return _normalize_intent(intent)


def _is_encirclement_command(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("encircle", "encirclement", "surround")) or any(token in text for token in ("围剿", "包围", "建筑"))


def _extract_coord(text: str) -> dict[str, Any]:
    if "WGS84_LATLON_ALT" in text:
        values = _extract_named_numbers(text, ("lat", "lon", "alt"))
        return default_coord_service.validate({"frame": "WGS84_LATLON_ALT", **values})
    values = _extract_named_numbers(text, ("x", "y", "z"))
    return default_coord_service.validate({"frame": "VBS_LOCAL_XYZ", **values})


def _extract_named_numbers(text: str, names: tuple[str, ...]) -> dict[str, float]:
    values: dict[str, float] = {}
    for name in names:
        match = re.search(rf"{name}\s*[:=]\s*(-?\d+(?:\.\d+)?)", text, re.I)
        values[name] = float(match.group(1)) if match else 0.0
    return values


def _normalize_intent(parsed: dict[str, Any]) -> dict[str, Any]:
    if "constraints" not in parsed:
        parsed["constraints"] = {"avoid_enemy": False, "maintain_formation": True, "allow_replan": True}
    if "actors" not in parsed or not parsed["actors"]:
        parsed["actors"] = [{"type": "group", "id": "p_4"}]
    destination = parsed.setdefault("destination", {"type": "absolute", "coord": {"frame": "VBS_LOCAL_XYZ", "x": 0.0, "y": 0.0, "z": 0.0}})
    if destination.get("type") == "absolute":
        destination["coord"] = default_coord_service.validate(destination["coord"])
    if parsed.get("intent") == "encircle_building" and "target" not in parsed:
        parsed["target"] = {"type": "building", "entry_coord": destination.get("coord")}
    return parsed


def prompt_preview(user_text: str) -> str:
    """Expose the exact prompt for tests/review without calling the LLM."""

    return json.dumps(_messages(user_text), ensure_ascii=False, indent=2)