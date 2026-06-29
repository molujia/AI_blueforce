import unittest

from zhibing.decision_layer.route_constraint_llm import explain_route_choices, parse_route_constraint


class ConstraintLLMTests(unittest.TestCase):
    def test_parse_sniper_risk_avoids_main_road(self) -> None:
        patch = parse_route_constraint("不要执行，因为大路有被狙击的风险")
        self.assertEqual(patch.action, "avoid")
        self.assertEqual(patch.target_type, "road_class")
        self.assertEqual(patch.target_id, "main_road")

    def test_parse_urgent_enemy_not_in_camp_ignores_enemy_zone(self) -> None:
        patch = parse_route_constraint("不要绕路，因为敌军不在营地，现在必须争分夺秒")
        self.assertEqual(patch.action, "ignore_zone")
        self.assertEqual(patch.target_type, "enemy_zone")
        self.assertEqual(patch.target_id, "enemy_1")

    def test_explain_route_choices_mentions_all_candidates(self) -> None:
        text = explain_route_choices([
            {"id": "route_main", "distance_m": 900, "risk_score": 60, "total_score": 1140, "labels": ["main_road"]},
            {"id": "route_side", "distance_m": 1040, "risk_score": 15, "total_score": 1263, "labels": ["side_path"]},
        ])
        self.assertIn("route_main", text)
        self.assertIn("route_side", text)


if __name__ == "__main__":
    unittest.main()

