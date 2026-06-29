"""Build a lightweight entity-relation-rule graph from local documents."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from zhibing.config import GRAPHRAG_CORPUS_PATHS
from zhibing.knowledge.document_loader import LoadedDocument, chunk_document, load_documents
from zhibing.knowledge.graphrag_store import GraphRAGStore, KnowledgeRule, KnowledgeTriple

DEFAULT_RULE_PATTERNS = (
    ("avoid_enemy_fire", ("enemy fire", "火力", "fire zone"), "Avoid known or suspected enemy fire zones during movement."),
    ("avoid_exposed_entry", ("入口", "entry", "exposed entrance"), "Do not approach exposed building entrances without assessment."),
    ("prefer_covered_route", ("cover", "concealment", "掩护", "隐蔽"), "Prefer covered and concealed routes when approaching buildings."),
    ("emergency_local_handling", ("sudden contact", "突发", "遇敌"), "Sudden contact and local avoidance are handled immediately by the lower runtime."),
    ("assess_before_entry", ("building", "建筑", "underground", "地下"), "Run situation assessment before entering or surrounding a target building."),
)

ENTITY_KEYWORDS = (
    "soldier", "group", "building", "entry", "enemy", "route", "fire", "cover", "obstacle", "地下", "建筑", "入口", "敌", "火力", "围剿", "路线"
)


def build_default_store() -> GraphRAGStore:
    return build_graphrag(GRAPHRAG_CORPUS_PATHS)


def build_graphrag(paths: Iterable[str | Path], *, inject_default_rules: bool = True) -> GraphRAGStore:
    documents = load_documents(paths)
    store = GraphRAGStore()
    for document in documents:
        ingest_document(store, document)
    if inject_default_rules and not store.rules:
        _inject_minimum_builtin_rules(store)
    return store


def ingest_document(store: GraphRAGStore, document: LoadedDocument) -> None:
    chunks = chunk_document(document)
    store.add_chunks(chunks)
    for chunk in chunks:
        text = chunk["text"]
        chunk_id = chunk["chunk_id"]
        _extract_keyword_triples(store, text, chunk_id)
        _extract_rules(store, text, chunk_id)


def _extract_keyword_triples(store: GraphRAGStore, text: str, chunk_id: str) -> None:
    lower = text.lower()
    present = [keyword for keyword in ENTITY_KEYWORDS if keyword.lower() in lower or keyword in text]
    for keyword in present:
        store.add_triple(KnowledgeTriple(keyword, "mentioned_in", chunk_id.split("#", 1)[0], chunk_id, confidence=0.7))
    if any(word in lower for word in ("avoid", "bypass")) or "避" in text:
        store.add_triple(KnowledgeTriple("movement", "should_avoid", "hazard", chunk_id, confidence=0.8))
    if "building" in lower or "建筑" in text:
        store.add_triple(KnowledgeTriple("mission", "may_target", "building", chunk_id, confidence=0.8))


def _extract_rules(store: GraphRAGStore, text: str, chunk_id: str) -> None:
    lower = text.lower()
    for rule_key, keywords, statement in DEFAULT_RULE_PATTERNS:
        if any(keyword.lower() in lower or keyword in text for keyword in keywords):
            rule_id = f"{rule_key}_{_short_hash(chunk_id)}"
            store.add_rule(KnowledgeRule(rule_id=rule_id, statement=statement, source_chunk_id=chunk_id, tags=(rule_key,), priority=8))
    for sentence in re.split(r"(?<=[.!?。！？])\s+|\n", text):
        stripped = sentence.strip()
        if len(stripped) < 12:
            continue
        lowered = stripped.lower()
        if any(marker in lowered for marker in ("must", "should", "avoid", "do not")) or any(marker in stripped for marker in ("必须", "应", "不得", "避免")):
            rule_id = f"source_rule_{_short_hash(chunk_id + stripped)}"
            store.add_rule(KnowledgeRule(rule_id=rule_id, statement=stripped[:500], source_chunk_id=chunk_id, tags=("source",), priority=6))


def _inject_minimum_builtin_rules(store: GraphRAGStore) -> None:
    chunk_id = "builtin_rules#chunk-0"
    store.add_chunks([{"chunk_id": chunk_id, "source_id": "builtin_rules", "text": "Avoid enemy fire zones, assess target building entrances, and handle sudden contact locally."}])
    for rule_key, _keywords, statement in DEFAULT_RULE_PATTERNS:
        store.add_rule(KnowledgeRule(rule_id=rule_key, statement=statement, source_chunk_id=chunk_id, tags=(rule_key,), priority=8))


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]