import unittest
from pathlib import Path

from zhibing.knowledge.benchmark import run_benchmarks
from zhibing.knowledge.llm_router import KnowledgeLLMRouter


class GraphRAGBenchmarkTests(unittest.TestCase):
    def test_benchmark_entrypoints_return_named_sections(self) -> None:
        report = run_benchmarks([Path("zhibing/knowledge/default_corpus")])
        for name in ("FormatBench", "RuleGroundingBench", "NoiseTripletBench", "LocalModelBench"):
            self.assertIn(name, report)
        self.assertGreaterEqual(report["RuleGroundingBench"]["case_count"], 4)
        self.assertIn("model_name", report["LocalModelBench"])

    def test_llm_router_reserves_ark_and_local_model_settings(self) -> None:
        summary = KnowledgeLLMRouter().provider_summary()
        self.assertEqual(summary["model_name"], "ep-20260615114505-247zc")
        self.assertIn("local_base_url", summary)


if __name__ == "__main__":
    unittest.main()