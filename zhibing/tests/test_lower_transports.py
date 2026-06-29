import unittest

from zhibing.adapter.http_transport import LowerSimHTTPTransport
from zhibing.adapter.socket_transport import LowerSimSocketTransport
from zhibing.config import LOWER_SIM_TRANSPORT


class LowerTransportTests(unittest.TestCase):
    def test_http_submit_payload_shape(self) -> None:
        transport = LowerSimHTTPTransport(base_url="http://lower-sim.test")
        payload = transport.build_submit_payload(task_id="task", request={"request_id": "req"}, sqf_statements=("line;",))
        self.assertEqual(payload["task_id"], "task")
        self.assertEqual(payload["sqf_statements"], ["line;"])

    def test_socket_envelope_shape(self) -> None:
        transport = LowerSimSocketTransport(host="127.0.0.1", port=9001)
        envelope = transport.build_envelope("TASK_QUERY", {"task_id": "task"})
        self.assertEqual(envelope["message_type"], "TASK_QUERY")
        self.assertEqual(envelope["payload"]["task_id"], "task")

    def test_config_defaults_to_http_for_deployment(self) -> None:
        self.assertEqual(LOWER_SIM_TRANSPORT, "http")


if __name__ == "__main__":
    unittest.main()