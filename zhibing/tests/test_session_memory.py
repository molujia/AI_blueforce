import tempfile
import unittest
from pathlib import Path

from zhibing.session_memory import SessionMemory


class SessionMemoryTests(unittest.TestCase):
    def test_session_can_store_messages_and_constraints(self) -> None:
        db_path = Path(tempfile.gettempdir()) / "zhibing_session_memory_test.sqlite3"
        if db_path.exists():
            db_path.unlink()
        memory = SessionMemory(db_path)
        session_id = memory.open_or_create_session("demo_encirclement_v0")
        memory.add_message(session_id, "user", "不要走大路")
        memory.add_constraint(session_id, {"constraint_id": "c1", "action": "avoid"})
        restored = memory.load_session(session_id)
        self.assertEqual(restored["messages"][0]["content"], "不要走大路")
        self.assertEqual(restored["constraints"][0]["constraint_id"], "c1")

    def test_reset_session_clears_context(self) -> None:
        db_path = Path(tempfile.gettempdir()) / "zhibing_session_memory_reset.sqlite3"
        if db_path.exists():
            db_path.unlink()
        memory = SessionMemory(db_path)
        session_id = memory.open_or_create_session("demo_encirclement_v0")
        memory.add_message(session_id, "user", "大路危险")
        memory.add_constraint(session_id, {"constraint_id": "c1"})
        memory.reset_session(session_id)
        restored = memory.load_session(session_id)
        self.assertEqual(restored["messages"], [])
        self.assertEqual(restored["constraints"], [])


if __name__ == "__main__":
    unittest.main()

