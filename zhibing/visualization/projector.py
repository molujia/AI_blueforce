"""Projection builder from decision-layer JSON to 2D map state."""

from __future__ import annotations

from typing import Any

from zhibing.core.coord_service import default_coord_service


def build_projection(*, intent_json: dict[str, Any], task_plan_json: dict[str, Any], status_response: dict[str, Any] | None) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    pending_intents: list[dict[str, Any]] = []
    status = status_response.get("status") if status_response else "PLANNED"
    actor_status = status or "PLANNED"
    status_actor = (status_response or {}).get("actor") or {}

    for step in task_plan_json.get("plan", []):
        actor = step.get("actor", {})
        if actor and not any(unit["id"] == actor.get("id") for unit in units):
            units.append({
                "id": actor.get("id"),
                "type": actor.get("type"),
                "status": actor_status,
                "position": status_actor.get("position"),
            })
        dest = _destination_from_step(step)
        bt_name = str(step.get("bt", {}).get("bt_name", ""))
        if dest:
            clean_dest = default_coord_service.validate(dest)
            routes.append({
                "id": step["step_id"],
                "task_type": step["task_type"],
                "bt_name": bt_name,
                "waypoints": [clean_dest],
            })
            targets.append({"id": f"{step['step_id']}_target", "kind": "building_entry_or_point", "coord": clean_dest})
        if bt_name.startswith("PENDING_") or not step.get("executable_by_adapter", True):
            pending_intents.append({"step_id": step.get("step_id"), "task_type": step.get("task_type"), "args": step.get("args", {}), "bt_name": bt_name})

    return {
        "mission_id": task_plan_json.get("mission_id", ""),
        "intent": intent_json.get("intent"),
        "units": units,
        "routes": routes,
        "targets": targets,
        "zones": _zones_from_knowledge(task_plan_json),
        "pending_intents": pending_intents,
        "task_state": {"state": status or "PLANNED", "return_code": status_response.get("return_code") if status_response else None},
    }


def _destination_from_step(step: dict[str, Any]) -> dict[str, Any] | None:
    args = step.get("args") or {}
    if isinstance(args.get("movePos"), dict):
        return args["movePos"]
    if isinstance(args.get("moveDest"), dict):
        return args["moveDest"]
    target = args.get("target") if isinstance(args.get("target"), dict) else {}
    if isinstance(target.get("entry_coord"), dict):
        return target["entry_coord"]
    return None


def _zones_from_knowledge(task_plan_json: dict[str, Any]) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    knowledge = task_plan_json.get("knowledge_context") or {}
    for rule in knowledge.get("rules", []):
        statement = str(rule.get("statement", "")).lower()
        if "fire" in statement or "火力" in statement:
            zones.append({"id": rule.get("rule_id", "risk_zone"), "kind": "risk_hint", "label": rule.get("statement", "enemy fire risk")})
    return zones

def build_demo_projection(
    scenario: dict[str, Any],
    route_candidates: list[dict[str, Any]],
    *,
    selected_route_id: str | None,
    session: dict[str, Any] | None,
    adapter_preview: dict[str, Any] | None = None,
    graphrag_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the 2D command UI projection for the v0 demo scene."""

    selected = None
    for candidate in route_candidates:
        candidate["selected"] = candidate.get("id") == selected_route_id
        if candidate["selected"]:
            selected = candidate
    return {
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["name"],
        "friendly": scenario["friendly"],
        "enemies": scenario["enemies"],
        "risk_zones": scenario["risk_zones"],
        "target": scenario["target"],
        "route_candidates": route_candidates,
        "selected_route_id": selected_route_id,
        "selected_route": selected,
        "session": session or {"messages": [], "constraints": [], "route_candidates": []},
        "adapter_preview": adapter_preview or _adapter_preview_from_demo(scenario, selected, session),
        "graphrag_status": graphrag_status or {"enabled": True, "mode": "local-usability", "source_hits": []},
        "task_state": {"state": "PLANNED", "return_code": None},
    }


def _adapter_preview_from_demo(scenario: dict[str, Any], selected: dict[str, Any] | None, session: dict[str, Any] | None) -> dict[str, Any]:
    constraints = (session or {}).get("constraints", [])
    return {
        "transport": "http",
        "actor_id": scenario["friendly"]["id"],
        "target": scenario["target"],
        "waypoints": (selected or {}).get("waypoints", []),
        "constraints": constraints,
        "task_type": "group_move_to_building_entry",
        "bt_name": "GrpMove",
        "pending_tactical_intent": "encirclement_assessment_and_attack",
    }