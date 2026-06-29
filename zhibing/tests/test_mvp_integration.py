import unittest

from zhibing.main import ZhibingDecisionSystem


class MVPIntegrationTests(unittest.TestCase):
    def test_mvp_success_command(self) -> None:
        system = ZhibingDecisionSystem()
        result = system.run_user_command("让p_4群组以速度10移动到指定坐标 VBS_LOCAL_XYZ {x:1000, y:500, z:0}")
        self.assertEqual(result.state, "SUCCEEDED")
        self.assertEqual(result.task_status_response["return_code"], "SUCCESS")
        self.assertIn(result.decision_log_id, system.repository.decision_logs)
        self.assertEqual(result.task_submit_request["task"]["bt_name"], "GrpMove")
        self.assertIn("selected grpmove", result.explanation.lower())

    def test_mvp_unreachable_triggers_replan(self) -> None:
        system = ZhibingDecisionSystem()
        result = system.run_user_command("让p_4群组以速度10移动到指定坐标 VBS_LOCAL_XYZ {x:9000, y:500, z:0}")
        self.assertEqual(result.state, "FAILED")
        self.assertEqual(result.task_status_response["return_code"], "UNREACHABLE")
        self.assertIsNotNone(result.replan_event)
        self.assertTrue(result.replan_event["replan_attempted"])
        self.assertEqual(result.replan_event["diagnosis"], "ROUTE_BLOCKED")


if __name__ == "__main__":
    unittest.main()
