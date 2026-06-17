from __future__ import annotations

from dataclasses import dataclass, field

from deepresearch.retrieval.identity import canonicalize_url, document_key
from deepresearch.retrieval.scoring import cosine_similarity
from deepresearch.schemas.evidence import RetrievedDocument

__all__ = [
    "RankedChunk",
    "canonicalize_url",
    "mmr_select",
    "rrf_fuse",
    "rrf_fuse_chunks",
]


@dataclass
class RankedChunk:
    chunk_id: str
    content: str
    title: str = ""
    source_url: str = ""
    score: float = 0.0
    embedding: list[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _doc_key(doc: RetrievedDocument) -> str:
    return document_key(doc)


def rrf_fuse(
    ranked_lists: list[list[RetrievedDocument]],
    *,
    rrf_k: int = 60,
    max_results: int = 20,
) -> list[RetrievedDocument]:
    """Reciprocal Rank Fusion over multiple ranked document lists.

    Each list is treated as an independent ranking. Documents are deduplicated
    by canonical URL (if available) or title + content hash.

    Args:
        ranked_lists: Per-query ranked document lists.
        rrf_k: Constant controlling score decay (default 60).
        max_results: Maximum documents to return.

    Returns:
        Fused and deduplicated document list sorted by RRF score descending.
    """
    scores: dict[str, float] = {}
    docs: dict[str, RetrievedDocument] = {}

    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):
            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            if key not in docs:
                docs[key] = doc

    ranked_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
    result: list[RetrievedDocument] = []
    for key in ranked_keys[:max_results]:
        doc = docs[key]
        result.append(
            doc.model_copy(
                update={"metadata": {**doc.metadata, "rrf_score": scores[key]}}
            )
        )
    return result


def rrf_fuse_chunks(
    ranked_lists: list[list[RankedChunk]],
    *,
    rrf_k: int = 60,
    max_results: int = 30,
) -> list[RankedChunk]:
    """RRF fusion for chunks. Dedup by chunk_id."""
    scores: dict[str, float] = {}
    chunks: dict[str, RankedChunk] = {}

    for ranked in ranked_lists:
        for rank, rc in enumerate(ranked, start=1):
            key = rc.chunk_id
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            if key not in chunks:
                chunks[key] = rc

    ranked_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
    result: list[RankedChunk] = []
    for key in ranked_keys[:max_results]:
        rc = chunks[key]
        result.append(
            RankedChunk(
                chunk_id=rc.chunk_id,
                content=rc.content,
                title=rc.title,
                source_url=rc.source_url,
                score=scores[key],
                embedding=rc.embedding,
                metadata={**rc.metadata, "rrf_score": scores[key]},
            )
        )
    return result


def mmr_select(
    candidates: list[RankedChunk],
    query_embedding: list[float],
    *,
    mmr_lambda: float = 0.7,
    max_results: int = 12,
) -> list[RankedChunk]:
    """Maximal Marginal Relevance selection.

    Selects candidates that maximize:
        λ * sim(q, d) - (1-λ) * max(sim(d, d_selected))

    Args:
        candidates: Ranked chunks with embeddings.
        query_embedding: The query embedding vector.
        mmr_lambda: Trade-off between relevance (1.0) and diversity (0.0).
        max_results: Maximum chunks to select.

    Returns:
        Selected chunks in MMR order.
    """
    if not candidates or not query_embedding:
        return []

    selected: list[RankedChunk] = []
    remaining = list(range(len(candidates)))
    query_sims = [
        c.score
        if "reranker_score" in c.metadata
        else (
            cosine_similarity(query_embedding, c.embedding) if c.embedding else c.score
        )
        for c in candidates
    ]

    while remaining and len(selected) < max_results:
        best_idx = -1
        best_score = -float("inf")
        for idx in remaining:
            relevance = query_sims[idx]
            if selected:
                max_sim = max(
                    (
                        cosine_similarity(candidates[idx].embedding, s.embedding)
                        if candidates[idx].embedding and s.embedding
                        else 0.0
                    )
                    for s in selected
                )
            else:
                max_sim = 0.0
            mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
        selected.append(candidates[best_idx])
        remaining.remove(best_idx)

    return selected
