from __future__ import annotations

import uuid

from deepresearch.retrieval.base import Retriever
from deepresearch.schemas.evidence import RetrievedDocument


class MockRetriever(Retriever):
    def __init__(self, docs: list[RetrievedDocument] | None = None) -> None:
        self._docs = docs or []
        self._calls: list[dict] = []

    @property
    def calls(self) -> list[dict]:
        return self._calls

    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str = "",
        task_id: str = "",
        top_k: int = 10,
    ) -> list[RetrievedDocument]:
        self._calls.append(
            {"queries": queries, "run_id": run_id, "task_id": task_id, "top_k": top_k}
        )

        if self._docs:
            return self._docs[:top_k]

        results: list[RetrievedDocument] = []
        for query in queries:
            results.append(
                RetrievedDocument(
                    id=str(uuid.uuid4()),
                    title=f"Mock result for: {query}",
                    content=(
                        f"This is mock content about {query}. "
                        "Recent advances in LLM agents show 40% improvement in "
                        "task completion rates. Multi-agent systems outperform "
                        "single-agent approaches on complex tasks."
                    ),
                    source_type="mock",
                    url=None,
                )
            )
        return results[:top_k]
