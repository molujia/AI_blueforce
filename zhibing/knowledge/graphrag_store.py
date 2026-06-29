"""In-memory graph store for doctrine-grounded retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class KnowledgeTriple:
    subject: str
    relation: str
    object: str
    source_chunk_id: str
    confidence: float = 1.0
    conflict: bool = False


@dataclass(frozen=True)
class KnowledgeRule:
    rule_id: str
    statement: str
    source_chunk_id: str
    tags: tuple[str, ...] = ()
    priority: int = 5


@dataclass
class GraphRAGStore:
    chunks: dict[str, dict[str, str]] = field(default_factory=dict)
    triples: list[KnowledgeTriple] = field(default_factory=list)
    rules: list[KnowledgeRule] = field(default_factory=list)

    def add_chunks(self, chunks: Iterable[dict[str, str]]) -> None:
        for chunk in chunks:
            self.chunks[chunk["chunk_id"]] = dict(chunk)

    def add_triple(self, triple: KnowledgeTriple) -> None:
        self.triples.append(triple)

    def add_rule(self, rule: KnowledgeRule) -> None:
        self.rules.append(rule)

    def query(self, query_text: str, *, limit: int = 8) -> dict[str, Any]:
        tokens = _tokens(query_text)
        scored_chunks = sorted(
            ((self._score_chunk(chunk, tokens), chunk) for chunk in self.chunks.values()),
            key=lambda item: item[0],
            reverse=True,
        )
        chunks = [chunk for score, chunk in scored_chunks if score > 0][:limit]
        source_ids = {chunk["chunk_id"] for chunk in chunks}
        rules = [rule for rule in self.rules if rule.source_chunk_id in source_ids or _matches(rule.statement, tokens)][:limit]
        triples = [triple for triple in self.triples if triple.source_chunk_id in source_ids or _matches(" ".join((triple.subject, triple.relation, triple.object)), tokens)][:limit]
        return {
            "query": query_text,
            "source_chunks": chunks,
            "rules": [rule.__dict__ for rule in rules],
            "triples": [triple.__dict__ for triple in triples],
            "conflicts": [triple.__dict__ for triple in triples if triple.conflict],
        }

    def inject_noise_triples(self, triples: Iterable[tuple[str, str, str]]) -> None:
        for index, (subject, relation, obj) in enumerate(triples):
            self.add_triple(KnowledgeTriple(subject, relation, obj, f"noise#chunk-{index}", confidence=0.1, conflict=True))

    def _score_chunk(self, chunk: dict[str, str], tokens: set[str]) -> int:
        haystack = chunk.get("text", "").lower()
        return sum(1 for token in tokens if token and token in haystack)


def _tokens(text: str) -> set[str]:
    lower = text.lower()
    words = set(re.findall(r"[a-zA-Z0-9_]{2,}", lower))
    for keyword in ("enemy", "fire", "building", "entry", "route", "avoid", "encirclement", "地下", "入口", "敌", "火力", "围剿", "建筑"):
        if keyword.lower() in lower or keyword in text:
            words.add(keyword.lower())
    return words


def _matches(text: str, tokens: set[str]) -> bool:
    lower = text.lower()
    return any(token in lower for token in tokens)