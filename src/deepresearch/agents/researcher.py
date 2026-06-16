from __future__ import annotations

import asyncio
import hashlib
import re
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
from deepresearch.prompts.provider import LocalPromptProvider, PromptProvider
from deepresearch.rerankers.base import RerankerClient
from deepresearch.retrieval.base import Retriever
from deepresearch.retrieval.chunking import chunk_text
from deepresearch.retrieval.dedup import dedup_documents
from deepresearch.retrieval.fetcher import WebFetcher
from deepresearch.retrieval.fusion import (
    RankedChunk,
    mmr_select,
    rrf_fuse,
    rrf_fuse_chunks,
)
from deepresearch.retrieval.query_expansion import expand_query
from deepresearch.schemas.evidence import EvidenceItem, RetrievedDocument
from deepresearch.schemas.task import TaskNode


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_with_char_map(text: str) -> tuple[str, list[int]]:
    """Normalize text and return ``(normalized_string, char_map)``.

    ``char_map[i]`` gives the original index in *text* that produced
    normalized character *i*.
    """
    lowered = text.lower()
    norm_chars: list[str] = []
    char_map: list[int] = []
    for orig_idx, ch in enumerate(lowered):
        if ch.isalnum() or ch == " ":
            norm_chars.append(ch)
            char_map.append(orig_idx)
        else:
            # Punctuation becomes a space placeholder
            norm_chars.append(" ")
            char_map.append(orig_idx)

    collapsed = re.sub(r"\s+", " ", "".join(norm_chars)).strip()
    if not collapsed:
        return "", []

    # Build the collapsed-char map: keep only the first mapping for each
    # run of whitespace, and every non-space mapping.
    result_map: list[int] = []
    prev_was_space = False
    for i, ch in enumerate(norm_chars):
        is_space = ch == " "
        if is_space:
            if not prev_was_space and result_map:
                # This is the boundary between words — record mapping
                result_map.append(char_map[i])
            prev_was_space = True
        else:
            result_map.append(char_map[i])
            prev_was_space = False

    result_map = result_map[: len(collapsed)]
    return collapsed, result_map


_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


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
        vector_top_k: int = 30,
        rerank_top_k: int = 8,
        rrf_k: int = 60,
        max_fused_docs: int = 20,
        max_fused_chunks: int = 30,
        mmr_lambda: float = 0.7,
        max_mmr_results: int = 12,
        fetch_concurrency: int = 5,
        progress: Callable[[str, dict[str, Any]], None] | None = None,
        prompt_provider: PromptProvider | None = None,
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
        self._vector_top_k = vector_top_k
        self._rerank_top_k = rerank_top_k
        self._rrf_k = rrf_k
        self._max_fused_docs = max_fused_docs
        self._max_fused_chunks = max_fused_chunks
        self._mmr_lambda = mmr_lambda
        self._max_mmr_results = max_mmr_results
        self._fetch_concurrency = fetch_concurrency
        self._progress = progress
        provider = prompt_provider or LocalPromptProvider(_DEFAULT_PROMPTS_DIR)
        self._system_prompt = provider.get("researcher")

    async def execute(self, task: TaskNode, *, run_id: str = "") -> dict:
        queries = await self._generate_queries(task)
        # Expand Chinese queries with English term aliases for cross-lingual retrieval
        expanded_queries: list[str] = []
        for q in queries:
            expanded_queries.extend(expand_query(q))
        queries = expanded_queries[: self._max_queries * 2]
        self._report_progress("queries_generated", {"query_count": len(queries)})
        per_query_results = await asyncio.gather(
            *(
                self._retriever.retrieve(
                    [q],
                    run_id=run_id,
                    task_id=task.task_id,
                    top_k=self._max_documents,
                )
                for q in queries
            )
        )
        pre_count = sum(len(r) for r in per_query_results)
        retrieved = rrf_fuse(
            per_query_results,
            rrf_k=self._rrf_k,
            max_results=min(self._max_fused_docs, self._max_documents),
        )
        self._report_progress(
            "retrieval_fused",
            {
                "pre_fusion_count": pre_count,
                "post_fusion_count": len(retrieved),
            },
        )
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
        query_texts = [query_text] + [q for q in queries[:3] if q != query_text]
        query_embeddings = (await self._embedding.embed(query_texts)).embeddings
        recall_lists = await asyncio.gather(
            *(
                self._memory.search(
                    emb,
                    run_id=run_id,
                    task_id=task.task_id,
                    source_type="chunk",
                    top_k=self._vector_top_k,
                )
                for emb in query_embeddings
            )
        )
        keyword_results = await self._memory.keyword_search(
            query_text,
            run_id=run_id,
            task_id=task.task_id,
            source_type="chunk",
            top_k=self._max_fused_chunks,
        )

        ranked_lists: list[list[RankedChunk]] = []
        for results in recall_lists:
            ranked_lists.append(
                [
                    RankedChunk(
                        chunk_id=r.entry.id,
                        content=r.entry.content,
                        title=r.entry.title,
                        source_url=r.entry.source_url,
                        score=r.score,
                        embedding=r.entry.embedding,
                        metadata=dict(r.entry.metadata),
                    )
                    for r in results
                ]
            )
        keyword_ranked = [
            RankedChunk(
                chunk_id=r.entry.id,
                content=r.entry.content,
                title=r.entry.title,
                source_url=r.entry.source_url,
                score=r.score,
                embedding=r.entry.embedding,
                metadata=dict(r.entry.metadata),
            )
            for r in keyword_results
        ]
        if keyword_ranked:
            ranked_lists.append(keyword_ranked)
        fused_chunks = rrf_fuse_chunks(
            ranked_lists,
            rrf_k=self._rrf_k,
            max_results=self._max_fused_chunks,
        )
        recalled_texts = [rc.content for rc in fused_chunks]
        self._report_progress(
            "chunk_rrf_fused",
            {
                "pre_fusion_count": sum(len(results) for results in recall_lists)
                + len(keyword_results),
                "post_fusion_count": len(fused_chunks),
                "query_count": len(query_texts),
                "keyword_count": len(keyword_results),
            },
        )

        reranked = await self._reranker.rerank(
            query_text,
            recalled_texts,
            top_k=self._rerank_top_k,
        )
        self._report_progress(
            "rerank_completed", {"result_count": len(reranked.results)}
        )
        reranked_chunks = [
            RankedChunk(
                chunk_id=fused_chunks[result.index].chunk_id,
                content=fused_chunks[result.index].content,
                title=fused_chunks[result.index].title,
                source_url=fused_chunks[result.index].source_url,
                score=result.score,
                embedding=fused_chunks[result.index].embedding,
                metadata={
                    **fused_chunks[result.index].metadata,
                    "reranker_score": result.score,
                },
            )
            for result in reranked.results
            if 0 <= result.index < len(fused_chunks)
        ]
        evidence_chunks = mmr_select(
            reranked_chunks,
            query_embeddings[0],
            mmr_lambda=self._mmr_lambda,
            max_results=self._max_mmr_results,
        )
        self._report_progress("mmr_selected", {"selected_count": len(evidence_chunks)})
        evidence = await self._extract_evidence(
            task,
            [
                SourceChunk(
                    chunk_id=rc.chunk_id,
                    document_id=str(rc.metadata.get("document_id", "")),
                    title=rc.title,
                    source_url=rc.source_url,
                    content=rc.content,
                    source_type=str(rc.metadata.get("source_type", "unknown")),
                    retrieved_at=str(rc.metadata.get("retrieved_at", "")),
                )
                for rc in evidence_chunks
            ],
        )
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
        queries = self._extract_query_list(data)

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
        raw_evidence = self._extract_evidence_list(data)
        if not raw_evidence:
            fallback = self._fallback_evidence_from_chunks(task, chunks)
            if fallback:
                self._report_progress(
                    "evidence_fallback_used", {"evidence_count": len(fallback)}
                )
            return fallback

        evidence: list[EvidenceItem] = []
        quality_rejected = False
        for raw in raw_evidence:
            if not isinstance(raw, dict):
                continue
            source = self._source_from_raw(source_map, raw.get("source_id"))
            if source is None:
                source = self._match_source_by_url(source_map, raw.get("source_url"))
            if source is None:
                self._report_progress(
                    "evidence_rejected",
                    {
                        "reason": "unknown_source",
                        "source_id": str(raw.get("source_id", "")),
                    },
                )
                continue
            quote = str(raw.get("quote", "")).strip()
            quote = self._exact_quote_from_source(quote, source.content)
            if not quote:
                self._report_progress(
                    "evidence_rejected",
                    {
                        "reason": "quote_not_found",
                        "source_id": str(raw.get("source_id", "")),
                    },
                )
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
                quality_rejected = True
                self._report_progress(
                    "evidence_quality_rejected",
                    {"evidence_id": item.evidence_id, "reason": reason},
                )
                continue
            evidence.append(item)
        if not evidence and not quality_rejected:
            fallback = self._fallback_evidence_from_chunks(task, chunks)
            if fallback:
                self._report_progress(
                    "evidence_fallback_used", {"evidence_count": len(fallback)}
                )
            return fallback
        return evidence

    def _fallback_evidence_from_chunks(
        self,
        task: TaskNode,
        chunks: list[SourceChunk],
        *,
        max_items: int = 5,
    ) -> list[EvidenceItem]:
        keywords = self._task_keywords(task)
        evidence: list[EvidenceItem] = []
        for index, chunk in enumerate(chunks, start=1):
            quote = self._best_sentence(chunk.content, keywords)
            if not quote:
                continue
            item = EvidenceItem(
                evidence_id=f"E{len(evidence) + 1}",
                task_id=task.task_id,
                claim=quote,
                quote=quote,
                citation=chunk.title or chunk.source_url or chunk.document_id,
                source_url=chunk.source_url or None,
                confidence=0.45,
                retrieved_at=chunk.retrieved_at,
                metadata={
                    "source_id": f"S{index}",
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "retrieved_at": chunk.retrieved_at,
                    "fallback": "sentence_from_ranked_chunk",
                },
            )
            passes, reason = self._quality_checker.check(item, chunk.content)
            if not passes:
                self._report_progress(
                    "evidence_quality_rejected",
                    {"evidence_id": item.evidence_id, "reason": reason},
                )
                continue
            evidence.append(item)
            if len(evidence) >= max_items:
                break
        return evidence

    @staticmethod
    def _task_keywords(task: TaskNode) -> set[str]:
        text = f"{task.description} {task.goal}".lower()
        # Latin tokens
        latin = set(re.findall(r"[a-z][a-z0-9_-]{3,}", text))
        latin -= {
            "what",
            "when",
            "where",
            "which",
            "with",
            "from",
            "into",
            "main",
            "extract",
            "evidence",
            "research",
            "analyze",
            "analysis",
        }
        # CJK unigrams + bigrams
        cjk_runs = re.findall(r"[㐀-鿿]+", text)
        cjk: set[str] = set()
        for run in cjk_runs:
            cjk.update(run)
            cjk.update(run[i : i + 2] for i in range(len(run) - 1))
        return latin | cjk

    @staticmethod
    def _best_sentence(content: str, keywords: set[str]) -> str:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?。！？])\s+", content)
            if sentence.strip()
        ]
        if not sentences:
            text = content.strip()
            return text[:500].strip() if len(text) >= 25 else ""

        def score(sentence: str) -> tuple[int, int]:
            normalized = sentence.lower()
            keyword_hits = sum(1 for keyword in keywords if keyword in normalized)
            return keyword_hits, min(len(sentence), 500)

        ranked = sorted(sentences, key=score, reverse=True)
        for sentence in ranked:
            keyword_hits, _ = score(sentence)
            if keywords and keyword_hits == 0:
                continue
            if len(sentence) >= 25:
                return sentence[:500].strip()
        return ""

    @staticmethod
    def _source_from_raw(
        source_map: dict[str, SourceChunk], source_id: object
    ) -> SourceChunk | None:
        if source_id is None:
            return None
        value = str(source_id).strip()
        candidates = [
            value,
            value.strip("[](){}"),
            value.upper(),
            value.strip("[](){}").upper(),
        ]
        for candidate in candidates:
            if candidate in source_map:
                return source_map[candidate]
        match = re.search(r"S\s*(\d+)", value, flags=re.IGNORECASE)
        if match:
            return source_map.get(f"S{match.group(1)}")
        return None

    @staticmethod
    def _exact_quote_from_source(quote: str, source_content: str) -> str:
        if not quote:
            return ""
        if quote in source_content:
            return quote

        quote_tokens = quote.split()
        if not quote_tokens:
            return ""
        pattern = r"\s+".join(re.escape(token) for token in quote_tokens)
        match = re.search(pattern, source_content, flags=re.IGNORECASE)
        if match:
            return source_content[match.start() : match.end()]

        # Fuzzy: normalize both sides, find match, map back via char offsets
        norm_source, char_map = _normalize_with_char_map(source_content)
        norm_quote = _normalize_text(quote)
        if not norm_quote:
            return ""
        start = norm_source.find(norm_quote)
        if start == -1:
            return ""
        end = start + len(norm_quote)
        orig_start = char_map[start]
        orig_end = char_map[end - 1] + 1  # inclusive end
        return source_content[orig_start:orig_end]

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

    @staticmethod
    def _extract_query_list(data: object) -> list[str]:
        if isinstance(data, dict):
            raw_queries = data.get("queries", [])
        elif isinstance(data, list):
            raw_queries = data
        else:
            raw_queries = []

        queries: list[str] = []
        if not isinstance(raw_queries, list):
            return queries
        for raw in raw_queries:
            if isinstance(raw, dict):
                value = raw.get("query") or raw.get("text") or raw.get("q")
            else:
                value = raw
            query = str(value).strip()
            if query:
                queries.append(query)
        return queries

    @staticmethod
    def _extract_evidence_list(data: object) -> list[object]:
        if isinstance(data, dict):
            raw_evidence = data.get("evidence", [])
        elif isinstance(data, list):
            raw_evidence = data
        else:
            raw_evidence = []
        return raw_evidence if isinstance(raw_evidence, list) else []

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
