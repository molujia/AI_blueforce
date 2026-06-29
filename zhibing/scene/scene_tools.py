"""Scene query tools used by the LLM decision layer.

These functions are the sanctioned facade for Layer 2 scene facts. The v0
implementation uses a deterministic demo scene, while keeping the same return
shape expected from a future lower simulation wrapper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zhibing.config import BT_REGISTRY_PATH
from zhibing.core.coord_service import CoordService, default_coord_service
from zhibing.core.timeout_service import compute_timeout
from zhibing.routing.constraint_patch import ConstraintPatch
from zhibing.routing.path_planner import plan_top_routes
from zhibing.scenario.demo_scenario import build_default_demo_scenario


def _load_registry() -> list[dict[str, Any]]:
    return json.loads(Path(BT_REGISTRY_PATH).read_text(encoding="utf-8"))


def get_actor_state(actor_id: str) -> dict[str, Any]:
    """Returns {id, type, position: CoordinateObject, health, status, current_bt, current_task_id}."""

    actor_type = "group" if actor_id.startswith("p_") or actor_id.startswith("grp") or actor_id.endswith("squad_1") else "soldier"
    scenario = build_default_demo_scenario()
    position = scenario["friendly"]["position"] if actor_id == scenario["friendly"]["id"] else {"frame": "VBS_LOCAL_XYZ", "x": 0.0, "y": 0.0, "z": 0.0}
    return {
        "id": actor_id,
        "type": actor_type,
        "position": default_coord_service.validate(position),
        "health": 1.0,
        "status": "ready",
        "current_bt": None,
        "current_task_id": None,
    }


def get_nearby_entities(position: dict[str, Any], radius_m: float) -> list[dict[str, Any]]:
    default_coord_service.validate(position)
    scenario = build_default_demo_scenario()
    return [scenario["friendly"], *scenario["enemies"], scenario["target"], *scenario["risk_zones"]]


def get_buildings(area: dict[str, Any]) -> list[dict[str, Any]]:
    default_coord_service.validate(area["position"] if "position" in area else area)
    target = build_default_demo_scenario()["target"]
    return [{"id": "building_target_1", "name": "target_building", "entrances": [target]}]


def get_building_entrances(building_id: str) -> list[dict[str, Any]]:
    target = build_default_demo_scenario()["target"]
    return [{"id": target["id"], "building_id": building_id, "coord": target["position"], "kind": target["kind"]}]


def get_enemy_state(area: dict[str, Any]) -> list[dict[str, Any]]:
    default_coord_service.validate(area["position"] if "position" in area else area)
    return build_default_demo_scenario()["enemies"]


def get_weather() -> dict[str, Any]:
    return {"condition": "clear", "weather_factor": 1.0, "visibility_m": 5000.0, "wind_mps": 0.0}


def route_plan(start: dict[str, Any], goal: dict[str, Any], constraints: dict[str, Any]) -> dict[str, Any]:
    """Returns a Top-N route plan using deterministic v0 demo geometry."""

    coord_service = CoordService()
    start_clean = coord_service.validate(start)
    goal_clean = coord_service.validate(goal)
    scenario = build_default_demo_scenario()
    candidates = [
        candidate.to_dict()
        for candidate in plan_top_routes(
            scenario,
            top_n=int(constraints.get("top_n", 3) or 3),
            constraints=_constraints_from_dict(constraints),
        )
    ]
    best = candidates[0]
    blocked_segments: list[str] = []
    passable = True
    goal_local = coord_service.to_vbs_local(goal_clean)
    if float(goal_local["x"]) >= 9000:
        passable = False
        blocked_segments.append("mock_blocked_corridor")
    speed = float(constraints.get("base_speed_mps") or 5.0)
    distance = float(best["distance_m"])
    return {
        "waypoints": best.get("waypoints") or [start_clean, goal_clean],
        "candidates": candidates,
        "selected_route_id": best["id"],
        "total_distance_m": distance,
        "risk_score": best.get("risk_score", 0.0),
        "blocked_segments": blocked_segments,
        "passable": passable,
        "estimated_time_s": distance / speed if speed > 0 else None,
    }


def estimate_move_time(route: dict[str, Any], speed_mps: float, formation: str, weather: dict[str, Any]) -> dict[str, int]:
    formation_factor = 0.75 if formation.lower() in {"wedge", "formation_triangle", "triangle"} else 1.0
    return compute_timeout(
        path_distance_m=float(route["total_distance_m"]),
        base_speed_mps=speed_mps,
        terrain_factor=1.0,
        weather_factor=float(weather.get("weather_factor", 1.0)),
        formation_factor=formation_factor,
        threat_factor=1.0,
    )


def lookup_bt(intent: str, actor_type: str) -> list[dict[str, Any]]:
    tags = _intent_tags(intent)
    ranked = []
    for entry in _load_registry():
        if not entry.get("active", True) or entry["scope"] != actor_type:
            continue
        capabilities = set(entry.get("capabilities", []))
        score = len(capabilities.intersection(tags))
        if score:
            item = dict(entry)
            item["_score"] = score
            ranked.append(item)
    ranked.sort(key=lambda item: (-int(item["_score"]), item["bt_name"] != "GrpMove", item["bt_name"]))
    return ranked


def validate_bt_args(bt_name: str, args: dict[str, Any]) -> dict[str, Any]:
    registry = {entry["bt_name"]: entry for entry in _load_registry()}
    if bt_name not in registry:
        return {"valid": False, "errors": ["BT_NOT_FOUND"], "warnings": []}
    entry = registry[bt_name]
    errors: list[str] = []
    warnings: list[str] = []
    for spec in entry.get("required_args", []):
        name = spec["name"]
        if name not in args:
            errors.append(f"MISSING_REQUIRED_ARG:{name}")
            continue
        _validate_arg_value(name, spec["type"], args[name], errors)
    for spec in entry.get("optional_args", []):
        if spec["name"] not in args:
            warnings.append(f"OPTIONAL_ARG_DEFAULT:{spec['name']}")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def query_obstacle(segment_id: str) -> dict[str, Any]:
    if segment_id == "mock_blocked_corridor":
        return {"passable": False, "reason": "mock terrain obstacle", "last_updated_at": "offline-mvp"}
    if segment_id == "risk_main_road_sniper":
        return {"passable": True, "reason": "sniper risk, avoid when constrained", "last_updated_at": "demo-v0"}
    return {"passable": True, "reason": "unknown or clear", "last_updated_at": "offline-mvp"}


def get_passable_routes(start: dict[str, Any], goal: dict[str, Any]) -> list[dict[str, Any]]:
    direct = route_plan(start, goal, {"avoid_enemy": False, "avoid_obstacles": True, "max_detour_factor": 2.0})
    return [direct] if direct["passable"] else []


def _constraints_from_dict(constraints: dict[str, Any]) -> list[ConstraintPatch]:
    patches: list[ConstraintPatch] = []
    for item in constraints.get("constraint_patches", []) or []:
        if isinstance(item, ConstraintPatch):
            patches.append(item)
        elif isinstance(item, dict):
            patches.append(
                ConstraintPatch(
                    constraint_id=str(item.get("constraint_id", "constraint")),
                    source_text=str(item.get("source_text", "")),
                    action=item.get("action", "priority"),
                    target_type=item.get("target_type", "route_metric"),
                    target_id=str(item.get("target_id", "balanced")),
                    weight_delta=float(item.get("weight_delta", 0.0)),
                    reason=str(item.get("reason", "")),
                    priority=item.get("priority"),
                )
            )
    return patches


def _intent_tags(intent: str) -> set[str]:
    text = intent.lower()
    tags: set[str] = set()
    if "move" in text or "移动" in text or "机动" in text or "围剿" in text or "encircle" in text:
        tags.add("group_move")
        tags.add("set_speed")
    if "formation" in text or "队形" in text:
        tags.add("set_formation")
    if "follow" in text or "跟随" in text:
        tags.add("formation_follow")
    return tags or {"group_move"}


def _validate_arg_value(name: str, arg_type: str, value: Any, errors: list[str]) -> None:
    if arg_type == "coordinate":
        try:
            default_coord_service.validate(value)
        except Exception as exc:
            errors.append(f"INVALID_COORDINATE:{name}:{exc}")
    elif arg_type == "coordinate_list":
        if not isinstance(value, list) or not value:
            errors.append(f"ARG_OUT_OF_RANGE:{name}")
        else:
            for item in value:
                try:
                    default_coord_service.validate(item)
                except Exception as exc:
                    errors.append(f"INVALID_COORDINATE:{name}:{exc}")
    elif arg_type == "number":
        if not isinstance(value, (int, float)):
            errors.append(f"ARG_OUT_OF_RANGE:{name}")
    elif arg_type == "formation":
        if not isinstance(value, dict):
            errors.append(f"ARG_OUT_OF_RANGE:{name}")