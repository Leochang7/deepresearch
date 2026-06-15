from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepresearch.agents.evidence_quality import (
    DefaultEvidenceQualityChecker,
    EvidenceQualityChecker,
)
from deepresearch.core.json_repair import parse_json
from deepresearch.embeddings.base import EmbeddingClient
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.memory.store import MemoryEntry, MemoryStore
from deepresearch.rerankers.base import RerankerClient
from deepresearch.retrieval.base import Retriever
from deepresearch.retrieval.chunking import chunk_text
from deepresearch.retrieval.dedup import dedup_documents
from deepresearch.retrieval.fetcher import WebFetcher
from deepresearch.schemas.evidence import EvidenceItem, RetrievedDocument
from deepresearch.schemas.task import TaskNode

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "researcher.md"


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    document_id: str
    title: str
    source_url: str
    content: str
    source_type: str
    retrieved_at: str = ""


class ResearchAgent:
    def __init__(
        self,
        llm: LLMClient,
        retriever: Retriever,
        memory: MemoryStore,
        embedding: EmbeddingClient,
        reranker: RerankerClient,
        *,
        fetcher: WebFetcher | None = None,
        quality_checker: EvidenceQualityChecker | None = None,
        max_queries: int = 5,
        max_documents: int = 20,
        max_chunks: int = 80,
        fetch_concurrency: int = 5,
        progress: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._memory = memory
        self._embedding = embedding
        self._reranker = reranker
        self._fetcher = fetcher or WebFetcher()
        self._quality_checker = quality_checker or DefaultEvidenceQualityChecker()
        self._max_queries = max_queries
        self._max_documents = max_documents
        self._max_chunks = max_chunks
        self._fetch_concurrency = fetch_concurrency
        self._progress = progress
        self._system_prompt = (
            _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""
        )

    async def execute(self, task: TaskNode, *, run_id: str = "") -> dict:
        queries = await self._generate_queries(task)
        self._report_progress("queries_generated", {"query_count": len(queries)})
        retrieved = await self._retriever.retrieve(
            queries,
            run_id=run_id,
            task_id=task.task_id,
            top_k=self._max_documents,
        )
        retrieved = dedup_documents(retrieved)[: self._max_documents]
        self._report_progress("retrieval_completed", {"document_count": len(retrieved)})
        documents = await self._fetch_documents(retrieved)
        self._report_progress("fetch_completed", {"document_count": len(documents)})
        chunks = self._build_chunks(documents)[: self._max_chunks]
        self._report_progress("chunking_completed", {"chunk_count": len(chunks)})

        if not chunks:
            return self._build_result(task, queries, [], 0, len(documents))

        chunk_embeddings = (
            await self._embedding.embed([chunk.content for chunk in chunks])
        ).embeddings
        self._report_progress(
            "chunk_embedding_completed", {"embedding_count": len(chunk_embeddings)}
        )
        if len(chunk_embeddings) != len(chunks):
            raise ValueError("Embedding response count does not match chunk count")

        await self._store_chunks(task, run_id, chunks, chunk_embeddings)

        query_text = task.goal or task.description
        query_embedding = (await self._embedding.embed([query_text])).embeddings[0]
        recalled = await self._memory.search(
            query_embedding,
            run_id=run_id,
            task_id=task.task_id,
            source_type="chunk",
            top_k=30,
        )
        self._report_progress(
            "memory_search_completed", {"result_count": len(recalled)}
        )
        recalled_chunks = [
            SourceChunk(
                chunk_id=result.entry.id,
                document_id=str(result.entry.metadata.get("document_id", "")),
                title=result.entry.title,
                source_url=result.entry.source_url,
                content=result.entry.content,
                source_type=str(result.entry.metadata.get("source_type", "unknown")),
                retrieved_at=str(result.entry.metadata.get("retrieved_at", "")),
            )
            for result in recalled
        ]

        reranked = await self._reranker.rerank(
            query_text,
            [chunk.content for chunk in recalled_chunks],
            top_k=8,
        )
        self._report_progress(
            "rerank_completed", {"result_count": len(reranked.results)}
        )
        evidence_chunks = [
            recalled_chunks[result.index]
            for result in reranked.results
            if 0 <= result.index < len(recalled_chunks)
        ]
        evidence = await self._extract_evidence(task, evidence_chunks)
        await self._store_evidence(task, run_id, evidence)
        self._report_progress(
            "evidence_extraction_completed", {"evidence_count": len(evidence)}
        )

        return self._build_result(
            task,
            queries,
            evidence,
            len(chunks),
            len(documents),
        )

    async def _generate_queries(self, task: TaskNode) -> list[str]:
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(
                role="user",
                content=f"Generate search queries for: {task.description}\nGoal: {task.goal}",
            ),
        ]
        response = await self._llm.chat(messages, json_mode=True)
        data = parse_json(response.content, strict=False)
        queries: list[str] = []
        if data and isinstance(data.get("queries"), list):
            queries = [
                str(query).strip() for query in data["queries"] if str(query).strip()
            ]

        supplements = [
            task.description,
            task.goal,
            f"{task.description} {task.goal}".strip(),
            f"{task.description} latest research",
            f"{task.description} evidence",
        ]
        for query in supplements:
            if query and query not in queries:
                queries.append(query)
            if len(queries) >= 3:
                break
        return queries[: self._max_queries]

    async def _fetch_documents(
        self, documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        semaphore = asyncio.Semaphore(self._fetch_concurrency)

        async def fetch_one(document: RetrievedDocument) -> RetrievedDocument:
            if not document.url:
                return document
            async with semaphore:
                result = await self._fetcher.fetch(document.url)
            if not result.success or not result.content:
                return document
            return document.model_copy(
                update={
                    "title": result.title or document.title,
                    "content": result.content,
                }
            )

        fetched = await asyncio.gather(*(fetch_one(document) for document in documents))
        return dedup_documents(fetched)

    def _report_progress(self, stage: str, metadata: dict[str, Any]) -> None:
        if self._progress is not None:
            self._progress(stage, metadata)

    def _build_chunks(self, documents: list[RetrievedDocument]) -> list[SourceChunk]:
        chunks: list[SourceChunk] = []
        seen: set[str] = set()
        for document in documents:
            for text in chunk_text(document.content):
                content_hash = hashlib.sha256(text.encode()).hexdigest()
                dedup_key = f"{document.url or document.id}:{content_hash}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                chunks.append(
                    SourceChunk(
                        chunk_id=f"chunk-{hashlib.sha256(dedup_key.encode()).hexdigest()[:24]}",
                        document_id=document.id,
                        title=document.title,
                        source_url=document.url or "",
                        content=text,
                        source_type=document.source_type,
                        retrieved_at=document.retrieved_at,
                    )
                )
        return chunks

    async def _store_chunks(
        self,
        task: TaskNode,
        run_id: str,
        chunks: list[SourceChunk],
        embeddings: list[list[float]],
    ) -> None:
        await self._memory.upsert(
            [
                MemoryEntry(
                    id=chunk.chunk_id,
                    run_id=run_id,
                    task_id=task.task_id,
                    title=chunk.title,
                    source_url=chunk.source_url,
                    content=chunk.content,
                    embedding=embedding,
                    source_type="chunk",
                    confidence=1.0,
                    metadata={
                        "document_id": chunk.document_id,
                        "source_type": chunk.source_type,
                        "retrieved_at": chunk.retrieved_at,
                    },
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]
        )

    async def _extract_evidence(
        self,
        task: TaskNode,
        chunks: list[SourceChunk],
    ) -> list[EvidenceItem]:
        if not chunks:
            return []

        source_map = {f"S{index}": chunk for index, chunk in enumerate(chunks, start=1)}
        context = "\n\n".join(
            (
                f"[{source_id}]\n"
                f"Title: {chunk.title}\n"
                f"URL: {chunk.source_url or 'local-source'}\n"
                f"Content: {chunk.content}"
            )
            for source_id, chunk in source_map.items()
        )
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(
                role="user",
                content=(
                    f"Task: {task.description}\n"
                    f"Goal: {task.goal}\n\n"
                    f"Reranked source chunks:\n{context}\n\n"
                    "Extract evidence as JSON. Every evidence item must include "
                    "one source_id from the provided chunks."
                ),
            ),
        ]
        response = await self._llm.chat(messages, json_mode=True)
        data = parse_json(response.content, strict=False)
        if not data or not isinstance(data.get("evidence"), list):
            return []

        evidence: list[EvidenceItem] = []
        for raw in data["evidence"]:
            if not isinstance(raw, dict):
                continue
            source = source_map.get(str(raw.get("source_id", "")))
            if source is None:
                source = self._match_source_by_url(source_map, raw.get("source_url"))
            if source is None:
                continue
            quote = str(raw.get("quote", "")).strip()
            if not quote or quote not in source.content:
                continue
            item = EvidenceItem(
                evidence_id=str(raw.get("evidence_id") or f"E{uuid.uuid4().hex[:8]}"),
                task_id=task.task_id,
                claim=str(raw.get("claim", "")).strip(),
                quote=quote,
                citation=source.title or source.source_url or source.document_id,
                source_url=source.source_url or None,
                confidence=self._bounded_confidence(raw.get("confidence", 0.5)),
                retrieved_at=source.retrieved_at,
                metadata={
                    "source_id": next(
                        key for key, value in source_map.items() if value == source
                    ),
                    "chunk_id": source.chunk_id,
                    "document_id": source.document_id,
                    "retrieved_at": source.retrieved_at,
                },
            )
            passes, reason = self._quality_checker.check(item, source.content)
            if not passes:
                self._report_progress(
                    "evidence_quality_rejected",
                    {"evidence_id": item.evidence_id, "reason": reason},
                )
                continue
            evidence.append(item)
        return evidence

    @staticmethod
    def _match_source_by_url(
        source_map: dict[str, SourceChunk], source_url: object
    ) -> SourceChunk | None:
        if not source_url:
            return None
        value = str(source_url)
        return next(
            (chunk for chunk in source_map.values() if chunk.source_url == value),
            None,
        )

    @staticmethod
    def _bounded_confidence(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5

    async def _store_evidence(
        self,
        task: TaskNode,
        run_id: str,
        evidence: list[EvidenceItem],
    ) -> None:
        if not evidence:
            return
        contents = [f"{item.claim}: {item.quote}" for item in evidence]
        embeddings = (await self._embedding.embed(contents)).embeddings
        if len(embeddings) != len(evidence):
            raise ValueError("Embedding response count does not match evidence count")
        await self._memory.upsert(
            [
                MemoryEntry(
                    id=f"{task.task_id}:{item.evidence_id}",
                    run_id=run_id,
                    task_id=task.task_id,
                    title=item.citation,
                    source_url=item.source_url or "",
                    content=content,
                    embedding=embedding,
                    source_type="memory",
                    confidence=item.confidence,
                    metadata={
                        **item.metadata,
                        "evidence_id": item.evidence_id,
                        "retrieved_at": item.retrieved_at,
                    },
                )
                for item, content, embedding in zip(
                    evidence, contents, embeddings, strict=True
                )
            ]
        )

    @staticmethod
    def _build_result(
        task: TaskNode,
        queries: list[str],
        evidence: list[EvidenceItem],
        chunk_count: int,
        doc_count: int,
    ) -> dict:
        serialized = [item.model_dump(mode="json") for item in evidence]
        return {
            "task_id": task.task_id,
            "queries": queries,
            "evidence": serialized,
            "evidence_ids": [item.evidence_id for item in evidence],
            "evidence_count": len(evidence),
            "information_insufficient": len(evidence) == 0,
            "chunk_count": chunk_count,
            "doc_count": doc_count,
        }
