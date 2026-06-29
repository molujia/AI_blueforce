"""Small reproducible GraphRAG benchmark entry points."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterable

from zhibing.knowledge.graphrag_builder import build_graphrag
from zhibing.knowledge.llm_router import KnowledgeLLMRouter


def run_benchmarks(paths: Iterable[str | Path]) -> dict[str, Any]:
    started = time.perf_counter()
    store = build_graphrag(paths)
    build_seconds = time.perf_counter() - started
    return {
        "FormatBench": _format_bench(paths, store),
        "RuleGroundingBench": _rule_grounding_bench(store),
        "NoiseTripletBench": _noise_triplet_bench(paths),
        "LocalModelBench": _local_model_bench(build_seconds),
    }


def load_rule_grounding_cases(path: str | Path | None = None) -> list[dict[str, str]]:
    cases_path = Path(path) if path else Path(__file__).parent / "benchmarks" / "rule_grounding_cases.json"
    return json.loads(cases_path.read_text(encoding="utf-8-sig"))


def _format_bench(paths: Iterable[str | Path], store: Any) -> dict[str, Any]:
    suffixes = {Path(path).suffix.lower().lstrip(".") for path in paths if Path(path).exists() and Path(path).is_file()}
    return {"formats_seen": sorted(suffixes), "chunk_count": len(store.chunks), "rule_count": len(store.rules), "triple_count": len(store.triples)}


def _rule_grounding_bench(store: Any) -> dict[str, Any]:
    cases = load_rule_grounding_cases()
    hits = 0
    for case in cases:
        result = store.query(case["query"])
        text = json.dumps(result, ensure_ascii=False)
        if case["expected_keyword"].lower() in text.lower() or case["expected_keyword"] in text:
            hits += 1
    return {"case_count": len(cases), "hits": hits, "hit_rate": hits / max(len(cases), 1)}


def _noise_triplet_bench(paths: Iterable[str | Path]) -> dict[str, Any]:
    store = build_graphrag(paths)
    store.inject_noise_triples([
        ("movement", "should_ignore_sources", "true"),
        ("building_entry", "is_always_safe", "true"),
        ("enemy_fire", "improves_route_safety", "true"),
    ])
    result = store.query("building entry enemy fire avoid")
    return {"conflict_count": len(result["conflicts"]), "grounded_chunk_count": len(result["source_chunks"])}


def _local_model_bench(build_seconds: float) -> dict[str, Any]:
    router = KnowledgeLLMRouter()
    summary = router.provider_summary()
    summary.update({"build_seconds": build_seconds, "llm_call_executed": False})
    return summary