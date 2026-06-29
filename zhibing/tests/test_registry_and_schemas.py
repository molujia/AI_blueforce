import json
import unittest
from pathlib import Path

from zhibing.config import BT_REGISTRY_PATH, SCHEMA_DIR


class RegistryAndSchemaTests(unittest.TestCase):
    def test_registry_has_four_mvp_entries(self) -> None:
        registry = json.loads(Path(BT_REGISTRY_PATH).read_text(encoding="utf-8"))
        self.assertEqual({entry["bt_name"] for entry in registry}, {"grpSimpleMoveNoAuto", "GrpMove", "GrpMove2", "grpFollowFormation"})
        self.assertTrue(all(entry["phase_available"] == "MVP" for entry in registry))

    def test_schema_files_exist(self) -> None:
        names = {
            "coordinate_object.schema.json",
            "task_submit_request.schema.json",
            "status_query_request.schema.json",
            "task_status_response.schema.json",
            "intent_json.schema.json",
            "task_plan_json.schema.json",
        }
        self.assertEqual(names, {path.name for path in Path(SCHEMA_DIR).glob("*.schema.json")})


if __name__ == "__main__":
    unittest.main()
