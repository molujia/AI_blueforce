import unittest

from zhibing.routing.constraint_patch import ConstraintPatch
from zhibing.routing.path_planner import plan_top_routes
from zhibing.scenario.demo_scenario import build_default_demo_scenario


class PathPlannerTests(unittest.TestCase):
    def test_default_planner_returns_top_routes(self) -> None:
        scenario = build_default_demo_scenario()
        routes = plan_top_routes(scenario, top_n=3, constraints=[])
        self.assertGreaterEqual(len(routes), 2)
        self.assertLess(routes[0].total_score, routes[-1].total_score)

    def test_avoid_main_road_constraint_changes_recommendation(self) -> None:
        scenario = build_default_demo_scenario()
        default_routes = plan_top_routes(scenario, top_n=3, constraints=[])
        constrained_routes = plan_top_routes(
            scenario,
            top_n=3,
            constraints=[
                ConstraintPatch(
                    constraint_id="c_avoid_main",
                    source_text="不要走大路，大路有狙击风险",
                    action="avoid",
                    target_type="road_class",
                    target_id="main_road",
                    weight_delta=200.0,
                    reason="用户要求规避大路",
                )
            ],
        )
        self.assertIn("main_road", default_routes[0].labels)
        self.assertNotIn("main_road", constrained_routes[0].labels)

    def test_ignore_enemy_zone_can_reduce_risk_penalty(self) -> None:
        scenario = build_default_demo_scenario()
        constrained_routes = plan_top_routes(
            scenario,
            top_n=3,
            constraints=[
                ConstraintPatch(
                    constraint_id="c_ignore_enemy",
                    source_text="敌军不在营地，必须争分夺秒",
                    action="ignore_zone",
                    target_type="enemy_zone",
                    target_id="enemy_1",
                    weight_delta=-80.0,
                    reason="用户要求忽略该敌区",
                )
            ],
        )
        self.assertGreaterEqual(len(constrained_routes), 2)
        self.assertEqual(constrained_routes[0].id, "route_main")


if __name__ == "__main__":
    unittest.main()

