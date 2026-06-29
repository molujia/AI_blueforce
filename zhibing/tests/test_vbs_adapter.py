import unittest

from zhibing.adapter.vbs_adapter import VBSAdapter


def _request(destination):
    return {
        "request_id": "req",
        "session_id": "sess",
        "actor": {"type": "group", "id": "p_4"},
        "task": {
            "task_type": "group_move",
            "btset_path": "CgfControl.btset",
            "bt_name": "GrpMove",
            "bt_scope": "group",
            "bt_args": {"movePos": destination, "speed": 10.0, "fmInfoTable": []},
        },
        "timeout_policy": {"expected_seconds": 1, "hard_timeout_seconds": 2, "stall_timeout_seconds": 1},
        "callback_policy": {"return_on": ["SUCCESS", "UNREACHABLE"]},
    }


class VBSAdapterTests(unittest.TestCase):
    def test_adapter_compiles_and_succeeds(self) -> None:
        adapter = VBSAdapter()
        destination = {"frame": "VBS_LOCAL_XYZ", "x": 1000.0, "y": 500.0, "z": 0.0}
        submit = adapter.submit_task(_request(destination), task_id="task")
        self.assertEqual(submit["status"], "ACKED")
        self.assertTrue(any("setBT" in line for line in submit["compiled_sqf"]))
        status = adapter.query_status({"task_id": "task"})
        self.assertEqual(status["return_code"], "SUCCESS")

    def test_adapter_classifies_unreachable(self) -> None:
        adapter = VBSAdapter()
        destination = {"frame": "VBS_LOCAL_XYZ", "x": 9000.0, "y": 500.0, "z": 0.0}
        adapter.submit_task(_request(destination), task_id="task")
        status = adapter.query_status({"task_id": "task"})
        self.assertEqual(status["status"], "FAILED")
        self.assertEqual(status["return_code"], "UNREACHABLE")


if __name__ == "__main__":
    unittest.main()
