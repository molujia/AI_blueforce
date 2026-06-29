"""Deterministic Top-N route planner for the v0 demonstration."""

from __future__ import annotations

import math
from typing import Any

from zhibing.routing.constraint_patch import ConstraintPatch
from zhibing.routing.road_graph import edge_labels, get_node_coord
from zhibing.scenario.models import RouteCandidate


def plan_top_routes(
    scenario: dict[str, Any],
    *,
    top_n: int = 3,
    constraints: list[ConstraintPatch] | None = None,
) -> list[RouteCandidate]:
    constraints = constraints or []
    graph = scenario["route_graph"]
    raw_routes = [
        ("route_main", ["start", "main_mid", "target"]),
        ("route_side", ["start", "side_a", "side_b", "target"]),
    ]
    candidates: list[RouteCandidate] = []
    for route_id, node_ids in raw_routes:
        waypoints = [get_node_coord(graph, node_id) for node_id in node_ids]
        labels = edge_labels(graph, node_ids)
        distance = _distance_of_waypoints(waypoints)
        risk = _risk_score(route_id, labels, constraints)
        time_score = distance / 5.0
        total = distance + risk + time_score
        candidates.append(
            RouteCandidate(
                id=route_id,
                waypoints=waypoints,
                distance_m=distance,
                risk_score=risk,
                time_score=time_score,
                total_score=total,
                labels=labels,
                constraint_hits=_constraint_hits(labels, constraints),
            )
        )
    candidates.sort(key=lambda item: item.total_score)
    return candidates[:top_n]


def scores_are_close(candidates: list[RouteCandidate], *, margin: float = 180.0) -> bool:
    if len(candidates) < 2:
        return False
    return abs(candidates[1].total_score - candidates[0].total_score) <= margin


def _distance_of_waypoints(waypoints: list[dict[str, Any]]) -> float:
    total = 0.0
    for left, right in zip(waypoints, waypoints[1:]):
        total += math.hypot(float(right["x"]) - float(left["x"]), float(right["y"]) - float(left["y"]))
    return total


def _risk_score(route_id: str, labels: list[str], constraints: list[ConstraintPatch]) -> float:
    score = 0.0
    if route_id == "route_main":
        score += 60.0
    if route_id == "route_side":
        score += 15.0
    for patch in constraints:
        if patch.action == "avoid" and patch.target_type == "road_class" and patch.target_id in labels:
            score += patch.weight_delta
        if patch.action == "ignore_zone" and patch.target_type == "enemy_zone":
            score += patch.weight_delta
        if patch.action == "priority" and patch.target_id == "time" and route_id == "route_main":
            score -= abs(patch.weight_delta)
    return max(score, 0.0)


def _constraint_hits(labels: list[str], constraints: list[ConstraintPatch]) -> list[str]:
    hits: list[str] = []
    for patch in constraints:
        if patch.target_type == "road_class" and patch.target_id in labels:
            hits.append(patch.constraint_id)
    return hits

