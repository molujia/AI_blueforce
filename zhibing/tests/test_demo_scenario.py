import unittest

from zhibing.scenario.demo_scenario import build_default_demo_scenario


class DemoScenarioTests(unittest.TestCase):
    def test_default_demo_has_required_objects(self) -> None:
        scenario = build_default_demo_scenario()
        self.assertEqual(scenario["friendly"]["id"], "blue_squad_1")
        self.assertGreaterEqual(len(scenario["enemies"]), 1)
        self.assertGreaterEqual(len(scenario["risk_zones"]), 1)
        self.assertEqual(scenario["target"]["kind"], "building_entry")
        self.assertGreaterEqual(len(scenario["route_graph"]["nodes"]), 4)
        self.assertGreaterEqual(len(scenario["route_graph"]["edges"]), 4)

    def test_demo_contains_main_and_side_route_labels(self) -> None:
        scenario = build_default_demo_scenario()
        labels = {edge["road_class"] for edge in scenario["route_graph"]["edges"]}
        self.assertIn("main_road", labels)
        self.assertIn("side_path", labels)


if __name__ == "__main__":
    unittest.main()

