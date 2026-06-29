import unittest

from zhibing.visualization.projector import build_projection


class VisualizationProjectionTests(unittest.TestCase):
    def test_projection_contains_units_routes_targets_and_pending_intents(self) -> None:
        plan = {
            "mission_id": "mission-1",
            "plan": [
                {
                    "step_id": "step_1_move_to_entry",
                    "task_type": "group_move_to_building_entry",
                    "actor": {"type": "group", "id": "p_4"},
                    "bt": {"btset_path": "CgfControl.btset", "bt_name": "GrpMove"},
                    "args": {"movePos": {"frame": "VBS_LOCAL_XYZ", "x": 1000, "y": 500, "z": 0}, "speed": 10},
                    "timeout_policy": {},
                    "executable_by_adapter": True,
                },
                {
                    "step_id": "step_3_attack_intent_pending_lower_bt",
                    "task_type": "attack_intent_pending_lower_bt",
                    "actor": {"type": "group", "id": "p_4"},
                    "bt": {"btset_path": "", "bt_name": "PENDING_LOWER_TACTICAL_BT"},
                    "args": {"intent": "move_and_attack", "target": {"entry_coord": {"frame": "VBS_LOCAL_XYZ", "x": 1000, "y": 500, "z": 0}}},
                    "timeout_policy": {},
                    "executable_by_adapter": False,
                },
            ],
        }
        projection = build_projection(intent_json={"intent": "encircle_building"}, task_plan_json=plan, status_response=None)
        self.assertEqual(projection["units"][0]["id"], "p_4")
        self.assertEqual(projection["routes"][0]["bt_name"], "GrpMove")
        self.assertEqual(projection["targets"][0]["coord"]["frame"], "VBS_LOCAL_XYZ")
        self.assertEqual(projection["pending_intents"][0]["task_type"], "attack_intent_pending_lower_bt")

    def test_projection_includes_scene_objects_and_route_candidates(self) -> None:
        from zhibing.routing.path_planner import plan_top_routes
        from zhibing.scenario.demo_scenario import build_default_demo_scenario
        from zhibing.visualization.projector import build_demo_projection

        scenario = build_default_demo_scenario()
        candidates = [item.to_dict() for item in plan_top_routes(scenario, top_n=3)]
        projection = build_demo_projection(scenario, candidates, selected_route_id=candidates[0]["id"], session=None)
        self.assertEqual(projection["friendly"]["id"], "blue_squad_1")
        self.assertGreaterEqual(len(projection["enemies"]), 1)
        self.assertGreaterEqual(len(projection["risk_zones"]), 1)
        self.assertGreaterEqual(len(projection["route_candidates"]), 2)
        self.assertEqual(projection["selected_route_id"], candidates[0]["id"])


if __name__ == "__main__":
    unittest.main()