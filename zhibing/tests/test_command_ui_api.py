import json
import os
import sys
import unittest
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zhibing_web.settings")

import django
from django.test import Client

django.setup()


class CommandUiApiTests(unittest.TestCase):
    def test_demo_scene_api_returns_projection(self) -> None:
        client = Client()
        response = client.get("/api/demo-scene")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["projection"]["friendly"]["id"], "blue_squad_1")

    def test_reset_session_api_returns_new_session_id(self) -> None:
        client = Client()
        response = client.post("/api/session/reset", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertIn("session_id", data)

    def test_route_constraint_api_changes_recommendation(self) -> None:
        client = Client()
        response = client.post(
            "/api/route-constraint",
            data=json.dumps({"message": "不要走大路，大路有狙击风险"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["constraint"]["target_id"], "main_road")
        self.assertNotIn("main_road", data["routes"][0]["labels"])


if __name__ == "__main__":
    unittest.main()

