from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from zhibing.decision_layer.route_constraint_llm import explain_route_choices, parse_route_constraint
from zhibing.main import ZhibingDecisionSystem
from zhibing.routing.constraint_patch import ConstraintPatch
from zhibing.routing.path_planner import plan_top_routes, scores_are_close
from zhibing.scenario.demo_scenario import build_default_demo_scenario
from zhibing.session_memory import SessionMemory
from zhibing.visualization.projector import build_demo_projection, build_projection

SYSTEM = ZhibingDecisionSystem()
MEMORY = SessionMemory()
SCENARIO_ID = "demo_encirclement_v0"
_TILE_DIR = Path(__file__).resolve().parents[1] / "zhibing_web" / "tile"


def index(request: Any):
    return render(request, "command_ui/index.html")


def serve_tile(request: Any, z: int, x: int, y: int):
    tile_path = _TILE_DIR / str(z) / str(x) / f"{y}.png"
    if not tile_path.is_file():
        raise Http404("Tile not found")
    with open(tile_path, "rb") as f:
        return HttpResponse(f.read(), content_type="image/png")


@csrf_exempt
@require_http_methods(["POST"])
def command(request: Any):
    data = json.loads(request.body.decode("utf-8"))
    result = SYSTEM.run_user_command(data["message"])
    intent_json = getattr(result, "intent_json", {})
    task_plan_json = getattr(result, "task_plan_json", {"mission_id": result.mission_id, "plan": []})
    projection = getattr(result, "projection", None) or build_projection(
        intent_json=intent_json,
        task_plan_json=task_plan_json,
        status_response=result.task_status_response,
    )
    return JsonResponse({
        "state": result.state,
        "task_id": result.task_id,
        "explanation": result.explanation,
        "task_submit_request": result.task_submit_request,
        "task_status_response": result.task_status_response,
        "projection": projection,
    })


def demo_scene(request: Any):
    session_id = _session_id_from_request(request) or MEMORY.latest_session_id(SCENARIO_ID) or MEMORY.open_or_create_session(SCENARIO_ID)
    scenario = build_default_demo_scenario()
    session = MEMORY.load_session(session_id)
    constraints = [_patch_from_dict(item) for item in session.get("constraints", [])]
    routes = [item.to_dict() for item in plan_top_routes(scenario, top_n=3, constraints=constraints)]
    selected_id = routes[0]["id"] if routes else None
    MEMORY.add_route_candidates(session_id, routes, selected_id)
    session = MEMORY.load_session(session_id)
    projection = build_demo_projection(scenario, routes, selected_route_id=selected_id, session=session)
    return JsonResponse({"session_id": session_id, "projection": projection})


@csrf_exempt
@require_http_methods(["POST"])
def reset_session(request: Any):
    data = _json_body(request)
    session_id = data.get("session_id") or MEMORY.open_or_create_session(SCENARIO_ID)
    if not data.get("session_id"):
        return JsonResponse({"session_id": session_id, "messages": [], "constraints": []})
    MEMORY.reset_session(session_id)
    return JsonResponse({"session_id": session_id, "messages": [], "constraints": []})


@csrf_exempt
@require_http_methods(["POST"])
def route_constraint(request: Any):
    data = _json_body(request)
    session_id = data.get("session_id") or MEMORY.latest_session_id(SCENARIO_ID) or MEMORY.open_or_create_session(SCENARIO_ID)
    message = str(data.get("message", ""))
    if message:
        MEMORY.add_message(session_id, "user", message)
    patch = parse_route_constraint(message)
    MEMORY.add_constraint(session_id, patch.to_dict())
    session = MEMORY.load_session(session_id)
    constraints = [_patch_from_dict(item) for item in session.get("constraints", [])]
    scenario = build_default_demo_scenario()
    candidates = plan_top_routes(scenario, top_n=3, constraints=constraints)
    routes = [item.to_dict() for item in candidates]
    selected_id = routes[0]["id"] if routes else None
    explanation = explain_route_choices(routes) if scores_are_close(candidates) else _direct_recommendation(routes)
    MEMORY.add_message(session_id, "assistant", explanation)
    MEMORY.add_route_candidates(session_id, routes, selected_id)
    session = MEMORY.load_session(session_id)
    projection = build_demo_projection(scenario, routes, selected_route_id=selected_id, session=session)
    return JsonResponse({
        "session_id": session_id,
        "constraint": patch.to_dict(),
        "routes": routes,
        "explanation": explanation,
        "projection": projection,
    })


def _json_body(request: Any) -> dict[str, Any]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _session_id_from_request(request: Any) -> str | None:
    return request.GET.get("session_id") or request.headers.get("X-Zhibing-Session")


def _patch_from_dict(item: dict[str, Any]) -> ConstraintPatch:
    return ConstraintPatch(
        constraint_id=str(item.get("constraint_id", "constraint")),
        source_text=str(item.get("source_text", "")),
        action=item.get("action", "priority"),
        target_type=item.get("target_type", "route_metric"),
        target_id=str(item.get("target_id", "balanced")),
        weight_delta=float(item.get("weight_delta", 0.0)),
        reason=str(item.get("reason", "")),
        priority=item.get("priority"),
    )


def _direct_recommendation(routes: list[dict[str, Any]]) -> str:
    if not routes:
        return "未生成可用路径。"
    best = routes[0]
    labels = "、".join(best.get("labels", [])) or "未标注"
    return f"推荐 {best['id']}：距离 {best['distance_m']:.0f} 米，风险 {best['risk_score']:.0f}，标签 {labels}。"