import unittest

from zhibing.main import ZhibingDecisionSystem
from zhibing.visualization.projector import build_projection


class ThreeLayerAlignmentTests(unittest.TestCase):
    def test_move_command_aligns_intent_visual_and_adapter(self) -> None:
        system = ZhibingDecisionSystem()
        result = system.run_user_command("order p_4 group speed 10 move to VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        projection = build_projection(intent_json=result.intent_json, task_plan_json=result.task_plan_json, status_response=result.task_status_response)
        self.assertEqual(result.task_submit_request["actor"]["id"], projection["units"][0]["id"])
        self.assertEqual(result.task_submit_request["task"]["bt_args"]["movePos"], projection["targets"][0]["coord"])
        self.assertIn("setBT", "\n".join(result.compiled_sqf))
        self.assertIn("setBBVariable", "\n".join(result.compiled_sqf))

    def test_encirclement_projection_marks_pending_attack_intent(self) -> None:
        system = ZhibingDecisionSystem()
        result = system.run_user_command("order p_4 encircle target building entry VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        projection = build_projection(intent_json=result.intent_json, task_plan_json=result.task_plan_json, status_response=result.task_status_response)
        self.assertEqual(result.task_submit_request["task"]["bt_name"], "GrpMove")
        self.assertTrue(any(item["task_type"] == "attack_intent_pending_lower_bt" for item in projection["pending_intents"]))
        self.assertEqual(result.task_plan_json["plan"][0]["task_type"], "group_move_to_building_entry")

    def test_constraint_changes_visual_route_and_adapter_preview(self) -> None:
        from zhibing.decision_layer.route_constraint_llm import parse_route_constraint
        from zhibing.routing.path_planner import plan_top_routes
        from zhibing.scenario.demo_scenario import build_default_demo_scenario
        from zhibing.visualization.projector import build_demo_projection

        scenario = build_default_demo_scenario()
        patch = parse_route_constraint("不要走大路，大路有狙击风险")
        routes = [item.to_dict() for item in plan_top_routes(scenario, top_n=3, constraints=[patch])]
        projection = build_demo_projection(scenario, routes, selected_route_id=routes[0]["id"], session={"constraints": [patch.to_dict()]})
        self.assertNotIn("main_road", projection["route_candidates"][0]["labels"])
        adapter_preview = projection["adapter_preview"]
        self.assertEqual(adapter_preview["waypoints"], projection["route_candidates"][0]["waypoints"])
        self.assertEqual(adapter_preview["constraints"][0]["target_id"], "main_road")


if __name__ == "__main__":
    unittest.main()