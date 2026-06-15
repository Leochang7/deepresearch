from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    id: str
    run_id: str = ""
    task_id: str = ""
    title: str = ""
    source_url: str = ""
    content: str = ""
    embedding: list[float] = field(default_factory=list)
    source_type: str = ""
    confidence: float = 0.0
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    entry: MemoryEntry
    score: float


class MemoryStore(ABC):
    @abstractmethod
    async def upsert(self, entries: list[MemoryEntry]) -> None: ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        *,
        run_id: str = "",
        task_id: str = "",
        source_type: str = "",
        min_confidence: float | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        *,
        run_id: str = "",
        task_id: str = "",
        source_type: str = "",
        min_confidence: float | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None: ...

    @abstractmethod
    async def snapshot(self, run_id: str) -> list[MemoryEntry]: ...


class MockMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self._entries: dict[str, MemoryEntry] = {}

    @property
    def count(self) -> int:
        return len(self._entries)

    async def upsert(self, entries: list[MemoryEntry]) -> None:
        for entry in entries:
            self._entries[entry.id] = entry

    async def search(
        self,
        query_embedding: list[float],
        *,
        run_id: str = "",
        task_id: str = "",
        source_type: str = "",
        min_confidence: float | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        candidates = list(self._entries.values())

        if run_id:
            candidates = [e for e in candidates if e.run_id == run_id]
        if task_id:
            candidates = [e for e in candidates if e.task_id == task_id]
        if source_type:
            candidates = [e for e in candidates if e.source_type == source_type]
        if min_confidence is not None:
            candidates = [e for e in candidates if e.confidence >= min_confidence]

        scored: list[SearchResult] = []
        for entry in candidates:
            if entry.embedding and query_embedding:
                score = _cosine_similarity(query_embedding, entry.embedding)
            else:
                score = 0.5
            scored.append(SearchResult(entry=entry, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            self._entries.pop(id_, None)

    async def snapshot(self, run_id: str) -> list[MemoryEntry]:
        return [e for e in self._entries.values() if e.run_id == run_id]

    async def keyword_search(
        self,
        query: str,
        *,
        run_id: str = "",
        task_id: str = "",
        source_type: str = "",
        min_confidence: float | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        candidates = list(self._entries.values())
        if run_id:
            candidates = [e for e in candidates if e.run_id == run_id]
        if task_id:
            candidates = [e for e in candidates if e.task_id == task_id]
        if source_type:
            candidates = [e for e in candidates if e.source_type == source_type]
        if min_confidence is not None:
            candidates = [e for e in candidates if e.confidence >= min_confidence]

        scored = [
            SearchResult(entry=entry, score=lexical_score(query, entry.content))
            for entry in candidates
        ]
        scored = [result for result in scored if result.score > 0]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:top_k]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def lexical_tokens(text: str) -> set[str]:
    normalized = text.lower()
    latin = set(re.findall(r"[a-z0-9]+", normalized))
    cjk_runs = re.findall(r"[\u3400-\u9fff]+", normalized)
    cjk: set[str] = set()
    for run in cjk_runs:
        cjk.update(run)
        cjk.update(run[index : index + 2] for index in range(len(run) - 1))
    return latin | cjk


def lexical_score(query: str, content: str) -> float:
    query_tokens = lexical_tokens(query)
    if not query_tokens:
        return 0.0
    content_tokens = lexical_tokens(content)
    return len(query_tokens & content_tokens) / len(query_tokens)
