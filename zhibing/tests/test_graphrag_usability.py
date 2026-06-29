import unittest

from zhibing.knowledge.graphrag_usability import local_file_usability_plan, official_quickstart_commands, query_local_test_files


class GraphRAGUsabilityTests(unittest.TestCase):
    def test_local_file_plan_includes_pdf_and_docx(self) -> None:
        plan = local_file_usability_plan()
        self.assertTrue(any(item["path"].endswith(".pdf") for item in plan["files"]))
        self.assertTrue(any(item["path"].endswith(".docx") for item in plan["files"]))

    def test_query_local_test_files_returns_source_hits(self) -> None:
        result = query_local_test_files("地下作战 建筑 入口")
        self.assertIn("hits", result)
        self.assertGreaterEqual(len(result["hits"]), 1)
        self.assertIn("source_id", result["hits"][0])

    def test_official_quickstart_is_manual(self) -> None:
        commands = official_quickstart_commands()
        self.assertTrue(any("graphrag index" in command for command in commands))


if __name__ == "__main__":
    unittest.main()

