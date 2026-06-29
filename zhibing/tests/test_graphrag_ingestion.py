import unittest
from pathlib import Path

from zhibing.knowledge.document_loader import load_document, load_documents
from zhibing.knowledge.graphrag_builder import build_graphrag
from zhibing.knowledge.graphrag_query import retrieve_knowledge


class GraphRAGIngestionTests(unittest.TestCase):
    def test_loads_pdf_and_docx_test_files(self) -> None:
        paths = [Path("test_files/ARN19656_ATP.pdf"), Path("test_files/地下作战.docx")]
        docs = load_documents(paths)
        self.assertEqual({doc.format for doc in docs}, {"pdf", "docx"})
        self.assertTrue(all(doc.text for doc in docs))

    def test_builds_grounded_store_with_rules_and_sources(self) -> None:
        store = build_graphrag([Path("zhibing/knowledge/default_corpus")])
        result = retrieve_knowledge({"intent": "encircle_building", "actors": [{"type": "group", "id": "p_4"}]}, {"route": {"distance_m": 10}}, store=store)
        self.assertGreaterEqual(len(result["rules"]), 1)
        self.assertGreaterEqual(len(result["source_chunks"]), 1)
        self.assertTrue(any("source_chunk_id" in rule for rule in result["rules"]))

    def test_single_document_loader_keeps_source_id(self) -> None:
        doc = load_document("zhibing/knowledge/default_corpus/urban_encirclement_rules.md")
        self.assertEqual(doc.source_id, "urban_encirclement_rules.md")
        self.assertIn("enemy fire", doc.text)


if __name__ == "__main__":
    unittest.main()