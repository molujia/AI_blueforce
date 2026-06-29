"""End-to-end wiring for the Zhibing upper-layer system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from zhibing.adapter.vbs_adapter import VBSAdapter
from zhibing.config import DEFAULT_BTSET_PATH
from zhibing.core.db import InMemoryRepository
from zhibing.core.task_state_machine import TaskState
from zhibing.decision_layer.module_a_intent import recognize_intent
from zhibing.decision_layer.module_b_scene import gather_scene
from zhibing.decision_layer.module_c_planner import create_task_plan, first_executable_step
from zhibing.decision_layer.module_d_bt_selector import select_bt
from zhibing.decision_layer.module_e_param_gen import generate_params
from zhibing.decision_layer.module_f_state_manager import StateManager
from zhibing.decision_layer.module_g_replanner import replan_after_failure
from zhibing.decision_layer.module_h_explainability import ExplainabilityLogger
from zhibing.hitl.interrupt_handler import check_hitl_required
from zhibing.visualization.projector import build_projection


@dataclass
class MissionRunResult:
    session_id: str
    mission_id: str
    task_id: str
    state: str
    task_submit_request: dict[str, Any]
    task_status_response: dict[str, Any]
    decision_log_id: str
    explanation: str
    compiled_sqf: tuple[str, ...]
    intent_json: dict[str, Any]
    task_plan_json: dict[str, Any]
    projection: dict[str, Any] | None = None
    replan_event: dict[str, Any] | None = None


class ZhibingDecisionSystem:
    """Upper-layer LLM decision layer plus task gateway/VBS adapter."""

    def __init__(self, repository: InMemoryRepository | None = None, adapter: VBSAdapter | None = None) -> None:
        self.repository = repository or InMemoryRepository()
        self.adapter = adapter or VBSAdapter()
        self.state_manager = StateManager()
        self.explainability = ExplainabilityLogger(self.repository)

    def run_user_command(self, user_text: str, *, user_id: str = "operator", scenario_id: str = "offline_mvp") -> MissionRunResult:
        intent = recognize_intent(user_text)
        interrupt = check_hitl_required(intent)
        if interrupt:
            raise RuntimeError(f"HITL required: {interrupt.trigger}")
        scene_context = gather_scene(intent)
        selected_bt, reason, alternatives = select_bt(intent, scene_context)
        selected_bt = dict(selected_bt)
        selected_bt["btset_path"] = DEFAULT_BTSET_PATH
        args, timeout_policy, parameters_sourced = generate_params(intent, selected_bt, scene_context)
        task_plan = create_task_plan(intent, selected_bt, args, timeout_policy)
        task_plan["knowledge_context"] = scene_context.get("knowledge_context", {})
        step = first_executable_step(task_plan)

        with self.repository.transaction():
            session_id = self.repository.create_session(user_id=user_id, scenario_id=scenario_id)
            mission_id = self.repository.create_mission_plan(session_id=session_id, user_intent=user_text, plan_json=task_plan)
            task_id = self.repository.create_task_instance(mission_id=mission_id, session_id=session_id, step=step)
            machine = self.state_manager.create(task_id=task_id, actor_id=step["actor"]["id"])
            decision_log_id = self.explainability.log_bt_selection(
                session_id=session_id,
                task_id=task_id,
                user_intent=user_text,
                intent_json=intent,
                selected_bt=selected_bt,
                selection_reason=reason,
                alternatives_considered=alternatives,
                parameters_sourced=parameters_sourced,
            )
            submit_request = self._build_submit_request(session_id=session_id, scenario_id=scenario_id, step=step)
            self.repository.log_vbs_request(task_id=task_id, request_type="submit", payload=submit_request)
            machine.on_submit_sent()
            self.repository.update_task_state(task_id, machine.state.value)

        submit_response = self.adapter.submit_task(submit_request, task_id=task_id)
        compiled_sqf = tuple(submit_response.get("compiled_sqf", ()))
        with self.repository.transaction():
            self.repository.log_vbs_return(request_id=submit_request["request_id"], task_id=task_id, payload=submit_response)
            if submit_response["status"] == "ACKED":
                machine.on_ack()
                self.repository.update_task_state(task_id, machine.state.value)
                machine.on_running()
                self.repository.update_task_state(task_id, machine.state.value)
            else:
                machine.on_load_error(str(submit_response["return_code"]))
                self.repository.update_task_state(task_id, machine.state.value)
                return self._result(
                    session_id,
                    mission_id,
                    task_id,
                    machine.state.value,
                    submit_request,
                    submit_response,
                    decision_log_id,
                    compiled_sqf,
                    intent,
                    task_plan,
                )

        status_query = {
            "request_id": str(uuid.uuid4()),
            "session_id": session_id,
            "task_id": task_id,
            "query_fields": ["task_status", "actor_position", "distance_to_goal", "active_bt", "active_node", "last_return_code", "progress_rate", "blocked_reason"],
        }
        self.repository.log_vbs_request(task_id=task_id, request_type="query", payload=status_query)
        status_response = self.adapter.query_status(status_query)
        replan_event = None
        with self.repository.transaction():
            self.repository.log_vbs_return(request_id=status_query["request_id"], task_id=task_id, payload=status_response)
            return_code = status_response.get("return_code")
            if return_code in {"SUCCESS", "UNREACHABLE", "SUBTASK_FAILED", "WAIT_UPPER"}:
                machine.on_return_code(str(return_code))
            elif status_response.get("status") == "TIMEOUT":
                machine.on_timeout()
            else:
                raise RuntimeError(f"Unsupported task status response: {status_response}")
            self.repository.update_task_state(
                task_id,
                machine.state.value,
                last_position=(status_response.get("actor") or {}).get("position"),
                last_progress_rate=(status_response.get("progress") or {}).get("progress_rate_mps"),
            )
            if machine.state == TaskState.FAILED and status_response.get("suggested_action") == "REPLAN_ROUTE":
                replan_event = replan_after_failure(self.repository, task_id=task_id, status_response=status_response)

        return self._result(
            session_id,
            mission_id,
            task_id,
            machine.state.value,
            submit_request,
            status_response,
            decision_log_id,
            compiled_sqf,
            intent,
            task_plan,
            replan_event,
        )

    def _build_submit_request(self, *, session_id: str, scenario_id: str, step: dict[str, Any]) -> dict[str, Any]:
        return {
            "request_id": str(uuid.uuid4()),
            "session_id": session_id,
            "scenario_id": scenario_id,
            "actor": step["actor"],
            "task": {
                "task_type": step["task_type"],
                "btset_path": step["bt"]["btset_path"],
                "bt_name": step["bt"]["bt_name"],
                "bt_scope": step["actor"]["type"],
                "bt_args": step["args"],
            },
            "timeout_policy": step["timeout_policy"],
            "callback_policy": {"return_on": ["SUCCESS", "UNREACHABLE", "SUBTASK_FAILED", "PARAM_ERROR", "BT_LOAD_ERROR", "ACTOR_NOT_FOUND", "WAIT_UPPER", "TIMEOUT"]},
        }

    def _result(
        self,
        session_id: str,
        mission_id: str,
        task_id: str,
        state: str,
        submit_request: dict[str, Any],
        status_response: dict[str, Any],
        decision_log_id: str,
        compiled_sqf: tuple[str, ...],
        intent_json: dict[str, Any],
        task_plan_json: dict[str, Any],
        replan_event: dict[str, Any] | None = None,
    ) -> MissionRunResult:
        projection = build_projection(intent_json=intent_json, task_plan_json=task_plan_json, status_response=status_response)
        return MissionRunResult(
            session_id=session_id,
            mission_id=mission_id,
            task_id=task_id,
            state=state,
            task_submit_request=submit_request,
            task_status_response=status_response,
            decision_log_id=decision_log_id,
            explanation=self.explainability.explain_task(task_id),
            compiled_sqf=compiled_sqf,
            intent_json=intent_json,
            task_plan_json=task_plan_json,
            projection=projection,
            replan_event=replan_event,
        )


def run_mission(user_text: str) -> MissionRunResult:
    return ZhibingDecisionSystem().run_user_command(user_text)


if __name__ == "__main__":
    result = run_mission("order p_4 group speed 10 move to VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
    print(result)