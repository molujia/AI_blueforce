import unittest

from zhibing.scene.scene_tools import get_enemy_state, route_plan


class SceneRouteToolsTests(unittest.TestCase):
    def test_enemy_state_returns_demo_enemy(self) -> None:
        enemies = get_enemy_state({"frame": "VBS_LOCAL_XYZ", "x": 0, "y": 0, "z": 0})
        self.assertGreaterEqual(len(enemies), 1)
        self.assertEqual(enemies[0]["id"], "enemy_1")

    def test_route_plan_returns_candidates(self) -> None:
        route = route_plan(
            {"frame": "VBS_LOCAL_XYZ", "x": 0, "y": 0, "z": 0},
            {"frame": "VBS_LOCAL_XYZ", "x": 900, "y": 0, "z": 0},
            {"top_n": 3},
        )
        self.assertIn("candidates", route)
        self.assertGreaterEqual(len(route["candidates"]), 2)


if __name__ == "__main__":
    unittest.main()

