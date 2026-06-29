"""Knowledge retrieval for intent and scene context."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from zhibing.knowledge.graphrag_builder import build_default_store
from zhibing.knowledge.graphrag_store import GraphRAGStore


@lru_cache(maxsize=1)
def get_default_store() -> GraphRAGStore:
    return build_default_store()


def retrieve_knowledge(intent_json: dict[str, Any], scene_context: dict[str, Any] | None = None, store: GraphRAGStore | None = None) -> dict[str, Any]:
    query_text = _query_text(intent_json, scene_context or {})
    active_store = store or get_default_store()
    result = active_store.query(query_text)
    return {
        "query": query_text,
        "rules": result["rules"],
        "triples": result["triples"],
        "source_chunks": result["source_chunks"],
        "conflicts": result["conflicts"],
    }


def _query_text(intent_json: dict[str, Any], scene_context: dict[str, Any]) -> str:
    parts = [str(intent_json.get("intent", ""))]
    destination = intent_json.get("destination") or {}
    parts.append(str(destination.get("type", "")))
    if "knowledge_query" in intent_json:
        parts.append(str(intent_json["knowledge_query"]))
    if scene_context.get("route"):
        parts.append("route building entry enemy fire avoid")
    if "encircle" in str(intent_json.get("intent", "")).lower() or "围剿" in str(intent_json):
        parts.append("encirclement building entry attack enemy fire")
    return " ".join(part for part in parts if part)