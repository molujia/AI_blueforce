import unittest

from zhibing.config import DEFAULT_BTSET_PATH
from zhibing.decision_layer.module_a_intent import recognize_intent
from zhibing.decision_layer.module_c_planner import create_task_plan, first_executable_step


class EncirclementDecompositionTests(unittest.TestCase):
    def test_encirclement_command_is_recognized(self) -> None:
        intent = recognize_intent("命令 p_4 前往目标建筑入口开展围剿任务 VBS_LOCAL_XYZ {x:1000, y:500, z:0}", prefer_llm=False)
        self.assertEqual(intent["intent"], "encircle_building")
        self.assertEqual(intent["actors"][0]["id"], "p_4")
        self.assertEqual(intent["target"]["entry_coord"]["frame"], "VBS_LOCAL_XYZ")

    def test_encirclement_decomposes_to_move_assess_pending_attack(self) -> None:
        intent = recognize_intent("order p_4 encircle target building entry VBS_LOCAL_XYZ {x:1000, y:500, z:0}", prefer_llm=False)
        selected_bt = {"btset_path": DEFAULT_BTSET_PATH, "bt_name": "GrpMove"}
        args = {"movePos": intent["destination"]["coord"], "speed": 5.0, "fmInfoTable": []}
        plan = create_task_plan(intent, selected_bt, args, {"hard_timeout_s": 100})
        self.assertEqual([step["task_type"] for step in plan["plan"]], ["group_move_to_building_entry", "situation_assessment", "attack_intent_pending_lower_bt"])
        self.assertEqual(first_executable_step(plan)["bt"]["bt_name"], "GrpMove")
        self.assertFalse(plan["plan"][1]["executable_by_adapter"])
        self.assertEqual(plan["plan"][2]["bt"]["bt_name"], "PENDING_LOWER_TACTICAL_BT")


if __name__ == "__main__":
    unittest.main()