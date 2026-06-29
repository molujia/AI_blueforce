"""Usability checks for GraphRAG-style knowledge ingestion and querying."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from zhibing.knowledge.graphrag_builder import build_graphrag

TEST_FILES_DIR = Path(__file__).resolve().parents[2] / "test_files"


def local_file_usability_plan() -> dict[str, Any]:
    files = [
        {"path": str(TEST_FILES_DIR / "地下作战.docx"), "kind": "docx"},
        {"path": str(TEST_FILES_DIR / "ARN19656_ATP.pdf"), "kind": "pdf"},
    ]
    return {"files": files, "acceptance": "build index and return source hits"}


def query_local_test_files(query: str) -> dict[str, Any]:
    paths = [item["path"] for item in local_file_usability_plan()["files"]]
    store = build_graphrag(paths, inject_default_rules=True)
    result = store.query(query, limit=5)
    chunks = result.get("source_chunks", [])
    if not chunks:
        chunks = list(store.chunks.values())[:5]
    hits = [
        {
            "source_id": chunk.get("source_id"),
            "chunk_id": chunk.get("chunk_id"),
            "text": str(chunk.get("text", ""))[:240],
        }
        for chunk in chunks
    ]
    return {"query": query, "hits": hits, "rules": result.get("rules", []), "triples": result.get("triples", [])}


def official_quickstart_commands() -> list[str]:
    """Return the manual official GraphRAG quickstart commands.

    These commands are intentionally not executed automatically because they can
    install packages and trigger LLM calls. The operator must approve network,
    proxy, model, and cost before running them.
    """

    return [
        "python -m pip install graphrag",
        "graphrag init --root ./graphrag_quickstart",
        "graphrag index --root ./graphrag_quickstart",
        'graphrag query --root ./graphrag_quickstart --method global --query "What are the main themes?"',
    ]