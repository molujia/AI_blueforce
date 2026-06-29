"""Interface ownership matrix for the upper system and lower simulation layer."""

from __future__ import annotations

from typing import Any


def get_interface_matrix() -> dict[str, dict[str, Any]]:
    """Return the contract boundary in a form suitable for docs and tests."""

    return {
        "Scene Query Tools": {
            "owner": "ZHIBING_OWNED",
            "description": "Upper-layer facade used by planning modules.",
            "zhibing_functions": [
                "get_actor_state",
                "get_nearby_entities",
                "get_buildings",
                "get_building_entrances",
                "get_enemy_state",
                "get_weather",
                "route_plan",
                "estimate_move_time",
                "lookup_bt",
                "validate_bt_args",
                "query_obstacle",
                "get_passable_routes",
            ],
            "lower_dependencies": [
                "GET /actors/{actor_id}/state",
                "POST /entities/nearby",
                "POST /buildings/query",
                "GET /buildings/{building_id}/entrances",
                "POST /enemy/query",
                "GET /environment/weather",
                "POST /routes/plan",
                "GET /obstacles/{segment_id}",
            ],
        },
        "IntentJSON": {"owner": "ZHIBING_OWNED"},
        "KnowledgeContext": {"owner": "ZHIBING_OWNED"},
        "TaskPlanJSON": {"owner": "ZHIBING_OWNED"},
        "BattlefieldProjection": {"owner": "ZHIBING_OWNED"},
        "GraphRAG Knowledge Tools": {"owner": "ZHIBING_OWNED"},
        "TaskSubmitRequest": {"owner": "SHARED_PROTOCOL"},
        "StatusQueryRequest": {"owner": "SHARED_PROTOCOL"},
        "TaskStatusResponse": {"owner": "SHARED_PROTOCOL"},
        "SocketEnvelope": {"owner": "SHARED_PROTOCOL"},
        "submit_sqf_plan": {"owner": "LOWER_SIM_REQUIRED"},
        "query_task": {"owner": "LOWER_SIM_REQUIRED"},
        "VBS Engine Runtime": {"owner": "LOWER_SIM_REQUIRED"},
        "BT Runtime": {"owner": "LOWER_SIM_REQUIRED"},
        "VBS Runtime Emergency Handling": {"owner": "LOWER_SIM_REQUIRED"},
    }


def interfaces_by_owner(owner: str) -> dict[str, dict[str, Any]]:
    matrix = get_interface_matrix()
    return {name: data for name, data in matrix.items() if data.get("owner") == owner}
