"""Default one-click deployment scenario for the v0 route demo."""

from __future__ import annotations

from typing import Any

from zhibing.scenario.models import BattlefieldUnit, RiskZone, TargetPoint


def coord(x: float, y: float) -> dict[str, float | str]:
    return {"frame": "VBS_LOCAL_XYZ", "x": float(x), "y": float(y), "z": 0.0}


def build_default_demo_scenario() -> dict[str, Any]:
    """Return a compact scene with a main road, side path, enemy, and target."""

    return {
        "scenario_id": "demo_encirclement_v0",
        "name": "默认围剿路径规划演示",
        "friendly": BattlefieldUnit("blue_squad_1", "AI士兵班组", "friendly", "squad", coord(0, 0)).to_dict(),
        "enemies": [
            BattlefieldUnit("enemy_1", "敌方火力点", "enemy", "fire_point", coord(520, 80), radius_m=90).to_dict()
        ],
        "risk_zones": [
            RiskZone("risk_main_road_sniper", "大路狙击风险区", "sniper_risk", coord(420, 0), 80, 70).to_dict()
        ],
        "target": TargetPoint("target_entry_1", "目标建筑入口", "building_entry", coord(900, 0)).to_dict(),
        "route_graph": {
            "nodes": [
                {"id": "start", "coord": coord(0, 0)},
                {"id": "main_mid", "coord": coord(450, 0)},
                {"id": "side_a", "coord": coord(260, 220)},
                {"id": "side_b", "coord": coord(650, 220)},
                {"id": "target", "coord": coord(900, 0)},
            ],
            "edges": [
                {"from": "start", "to": "main_mid", "road_class": "main_road"},
                {"from": "main_mid", "to": "target", "road_class": "main_road"},
                {"from": "start", "to": "side_a", "road_class": "side_path"},
                {"from": "side_a", "to": "side_b", "road_class": "side_path"},
                {"from": "side_b", "to": "target", "road_class": "side_path"},
            ],
        },
    }

