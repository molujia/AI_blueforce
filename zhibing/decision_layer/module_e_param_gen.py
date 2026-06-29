"""Module E: parameter generation and pre-submit validation."""

from __future__ import annotations

from typing import Any

from zhibing.decision_layer.module_d_bt_selector import BTSelectionError
from zhibing.scene import scene_tools


class ParameterGenerationError(RuntimeError):
    """Raised when required BT arguments cannot be filled."""


def generate_params(intent_json: dict[str, Any], selected_bt: dict[str, Any], scene_context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    destination = intent_json.get("destination", {})
    if destination.get("type") != "absolute":
        raise ParameterGenerationError("MVP supports absolute destinations only.")
    coord = destination["coord"]
    speed = float(intent_json.get("speed_mps", 5.0))
    bt_name = selected_bt["bt_name"]
    parameters_sourced: dict[str, Any] = {}
    if bt_name == "GrpMove":
        args = {"movePos": coord, "speed": speed, "fmInfoTable": []}
        parameters_sourced = {
            "movePos": {"value": coord, "source": "user_input"},
            "speed": {"value": speed, "source": "user_input" if "speed_mps" in intent_json else "default"},
            "fmInfoTable": {"value": [], "source": "default"},
        }
    elif bt_name == "grpSimpleMoveNoAuto":
        args = {"moveDest": coord, "formation": {"name": "Formation_Triangle", "ratio": 5.0}}
        parameters_sourced = {
            "moveDest": {"value": coord, "source": "user_input"},
            "formation": {"value": args["formation"], "source": "default"},
        }
    elif bt_name == "GrpMove2":
        args = {"movePosArr": [coord], "speed": speed, "dir": 0.0}
        parameters_sourced = {
            "movePosArr": {"value": args["movePosArr"], "source": "inferred"},
            "speed": {"value": speed, "source": "user_input" if "speed_mps" in intent_json else "default"},
            "dir": {"value": 0.0, "source": "default"},
        }
    else:
        raise BTSelectionError(f"BT {bt_name} has no MVP parameter generator.")
    validation = scene_tools.validate_bt_args(bt_name, args)
    if not validation["valid"]:
        raise ParameterGenerationError("; ".join(validation["errors"]))
    route = scene_context["route"]
    weather = scene_context["weather"]
    timeout_policy = scene_tools.estimate_move_time(route, speed, "Formation_Triangle", weather)
    return args, timeout_policy, parameters_sourced

