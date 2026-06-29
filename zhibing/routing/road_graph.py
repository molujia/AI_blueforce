"""Small route graph helpers for the demo path planner."""

from __future__ import annotations

from typing import Any


def get_node_coord(route_graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in route_graph["nodes"]:
        if node["id"] == node_id:
            return node["coord"]
    raise KeyError(f"route graph node not found: {node_id}")


def edge_labels(route_graph: dict[str, Any], node_path: list[str]) -> list[str]:
    labels: list[str] = []
    pairs = set(zip(node_path, node_path[1:]))
    for edge in route_graph["edges"]:
        if (edge["from"], edge["to"]) in pairs or (edge["to"], edge["from"]) in pairs:
            labels.append(edge.get("road_class", "unknown"))
    return labels

