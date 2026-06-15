from __future__ import annotations

from deepresearch.rerankers.base import RerankerClient, RerankerResponse, RerankResult


class MockRerankerClient(RerankerClient):
    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str | None = None,
        top_k: int | None = None,
    ) -> RerankerResponse:
        query_lower = query.lower()
        scored = []
        for i, doc in enumerate(documents):
            overlap = sum(1 for w in query_lower.split() if w in doc.lower())
            score = min(1.0, 0.3 + overlap * 0.2)
            scored.append(RerankResult(index=i, score=score, text=doc))

        scored.sort(key=lambda r: r.score, reverse=True)

        if top_k is not None:
            scored = scored[:top_k]

        return RerankerResponse(
            results=scored,
            model="mock-reranker",
            usage={"prompt_tokens": len(query) + sum(len(d) for d in documents)},
        )
