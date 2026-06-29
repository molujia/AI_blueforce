import json
import unittest
from pathlib import Path

from zhibing.interfaces.interface_ownership import get_interface_matrix


class InterfaceOwnershipTests(unittest.TestCase):
    def test_shared_and_lower_interfaces_are_explicit(self) -> None:
        matrix = get_interface_matrix()
        self.assertEqual(matrix["StatusQueryRequest"]["owner"], "SHARED_PROTOCOL")
        self.assertEqual(matrix["TaskStatusResponse"]["owner"], "SHARED_PROTOCOL")
        self.assertEqual(matrix["submit_sqf_plan"]["owner"], "LOWER_SIM_REQUIRED")
        self.assertEqual(matrix["query_task"]["owner"], "LOWER_SIM_REQUIRED")

    def test_scene_tools_are_zhibing_facades_with_lower_dependencies(self) -> None:
        matrix = get_interface_matrix()
        scene = matrix["Scene Query Tools"]
        self.assertEqual(scene["owner"], "ZHIBING_OWNED")
        self.assertIn("get_actor_state", scene["zhibing_functions"])
        self.assertIn("GET /actors/{actor_id}/state", scene["lower_dependencies"])

    def test_simulation_contract_schema_is_machine_readable(self) -> None:
        path = Path("zhibing/interfaces/simulation_contract.schema.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("SubmitSQFPlan", data["definitions"])
        self.assertIn("SocketEnvelope", data["definitions"])


if __name__ == "__main__":
    unittest.main()
