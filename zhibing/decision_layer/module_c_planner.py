"""Module C: TaskPlanJSON generation."""

from __future__ import annotations

import uuid
from typing import Any


def create_single_step_plan(intent_json: dict[str, Any], selected_bt: dict[str, Any], args: dict[str, Any], timeout_policy: dict[str, Any]) -> dict[str, Any]:
    actor = intent_json["actors"][0]
    return {
        "mission_id": str(uuid.uuid4()),
        "plan": [
            _executable_step(
                step_id="step_1",
                task_type=intent_json["intent"],
                actor=actor,
                selected_bt=selected_bt,
                args=args,
                timeout_policy=timeout_policy,
                depends_on=[],
            )
        ],
    }


def create_task_plan(intent_json: dict[str, Any], selected_bt: dict[str, Any], args: dict[str, Any], timeout_policy: dict[str, Any]) -> dict[str, Any]:
    if intent_json.get("intent") != "encircle_building":
        return create_single_step_plan(intent_json, selected_bt, args, timeout_policy)
    actor = intent_json["actors"][0]
    mission_id = str(uuid.uuid4())
    move_step = _executable_step(
        step_id="step_1_move_to_entry",
        task_type="group_move_to_building_entry",
        actor=actor,
        selected_bt=selected_bt,
        args=args,
        timeout_policy=timeout_policy,
        depends_on=[],
    )
    assessment_step = {
        "step_id": "step_2_situation_assessment",
        "task_type": "situation_assessment",
        "actor": actor,
        "depends_on": [move_step["step_id"]],
        "bt": {"btset_path": "", "bt_name": "PENDING_UPPER_SCENE_ASSESSMENT"},
        "args": {"target": intent_json.get("target", {}), "knowledge_query": intent_json.get("knowledge_query", "")},
        "timeout_policy": {},
        "executable_by_adapter": False,
        "metadata": {"reason": "No lower tactical assessment BT is available in the current registry."},
    }
    attack_step = {
        "step_id": "step_3_attack_intent_pending_lower_bt",
        "task_type": "attack_intent_pending_lower_bt",
        "actor": actor,
        "depends_on": [assessment_step["step_id"]],
        "bt": {"btset_path": "", "bt_name": "PENDING_LOWER_TACTICAL_BT"},
        "args": {"intent": "move_and_attack", "target": intent_json.get("target", {})},
        "timeout_policy": {},
        "executable_by_adapter": False,
        "metadata": {"reason": "Current BT registry only supports move and simple attack/movement primitives."},
    }
    return {"mission_id": mission_id, "plan": [move_step, assessment_step, attack_step]}


def first_executable_step(task_plan: dict[str, Any]) -> dict[str, Any]:
    for step in task_plan.get("plan", []):
        if step.get("executable_by_adapter", True) and not str(step.get("bt", {}).get("bt_name", "")).startswith("PENDING_"):
            return step
    raise ValueError("TaskPlanJSON has no executable adapter step.")


def _executable_step(
    *,
    step_id: str,
    task_type: str,
    actor: dict[str, Any],
    selected_bt: dict[str, Any],
    args: dict[str, Any],
    timeout_policy: dict[str, Any],
    depends_on: list[str],
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "task_type": task_type,
        "actor": actor,
        "depends_on": depends_on,
        "bt": {"btset_path": selected_bt["btset_path"], "bt_name": selected_bt["bt_name"]},
        "args": args,
        "timeout_policy": timeout_policy,
        "executable_by_adapter": True,
    }