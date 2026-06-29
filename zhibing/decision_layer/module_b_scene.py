"""Module B: scene query orchestration."""

from __future__ import annotations

from typing import Any

from zhibing.knowledge.graphrag_query import retrieve_knowledge
from zhibing.scene import scene_tools


def gather_scene(intent_json: dict[str, Any]) -> dict[str, Any]:
    actor = intent_json["actors"][0]
    actor_state = scene_tools.get_actor_state(actor["id"])
    weather = scene_tools.get_weather()
    destination = intent_json.get("destination", {})
    route = None
    if destination.get("type") == "absolute":
        route = scene_tools.route_plan(
            actor_state["position"],
            destination["coord"],
            {
                "avoid_enemy": intent_json.get("constraints", {}).get("avoid_enemy", False),
                "avoid_obstacles": True,
                "max_detour_factor": 2.0,
                "base_speed_mps": float(intent_json.get("speed_mps", 5.0)),
            },
        )
    bt_candidates = scene_tools.lookup_bt(intent_json["intent"], actor["type"])
    scene_context = {"actor_state": actor_state, "weather": weather, "route": route, "bt_candidates": bt_candidates}
    scene_context["knowledge_context"] = retrieve_knowledge(intent_json, scene_context)
    return scene_context