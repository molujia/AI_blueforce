"""LLM-facing route constraint parser with deterministic fallback behavior."""

from __future__ import annotations

import hashlib
from typing import Any

from zhibing.routing.constraint_patch import ConstraintPatch


def parse_route_constraint(user_text: str) -> ConstraintPatch:
    """Parse a user route instruction into an auditable constraint patch.

    The v0 implementation is deterministic for repeatable tests. A live LLM can
    be wired behind this function later, but must still return this schema.
    """

    text = user_text.lower()
    constraint_id = "c_" + hashlib.sha1(user_text.encode("utf-8")).hexdigest()[:8]
    if "大路" in user_text or "main road" in text or "狙击" in user_text:
        return ConstraintPatch(
            constraint_id=constraint_id,
            source_text=user_text,
            action="avoid",
            target_type="road_class",
            target_id="main_road",
            weight_delta=200.0,
            reason="用户指出大路存在狙击或暴露风险",
        )
    if "不在营地" in user_text or "争分夺秒" in user_text or "不要绕路" in user_text:
        return ConstraintPatch(
            constraint_id=constraint_id,
            source_text=user_text,
            action="ignore_zone",
            target_type="enemy_zone",
            target_id="enemy_1",
            weight_delta=-80.0,
            reason="用户要求降低敌方营地区域对路径的影响并优先时间",
            priority="time",
        )
    return ConstraintPatch(
        constraint_id=constraint_id,
        source_text=user_text,
        action="priority",
        target_type="route_metric",
        target_id="balanced",
        weight_delta=0.0,
        reason="未识别到明确重规划约束，保持均衡评分",
    )


def explain_route_choices(candidates: list[dict[str, Any]]) -> str:
    lines = ["候选路径分数接近，请选择一条路线："]
    for index, item in enumerate(candidates, start=1):
        labels = "、".join(item.get("labels", [])) or "未标注"
        lines.append(
            f"{index}. {item['id']}：距离 {item['distance_m']:.0f} 米，"
            f"风险 {item['risk_score']:.0f}，总分 {item['total_score']:.0f}，标签 {labels}。"
        )
    lines.append("可回复编号选择路线，也可输入新的约束重新规划。")
    return "\n".join(lines)