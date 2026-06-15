from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx

from deepresearch.retrieval.base import Retriever
from deepresearch.schemas.evidence import RetrievedDocument


class TavilyWebSearchRetriever(Retriever):
    def __init__(
        self,
        *,
        api_key: str = "",
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries

    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str = "",
        task_id: str = "",
        top_k: int = 10,
    ) -> list[RetrievedDocument]:
        results = await asyncio.gather(
            *(self._search(query, top_k=min(top_k, 5)) for query in queries)
        )
        all_docs = [document for documents in results for document in documents]
        return all_docs[:top_k]

    async def _search(self, query: str, top_k: int = 5) -> list[RetrievedDocument]:
        url = "https://api.tavily.com/search"
        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query,
            "max_results": top_k,
            "include_answer": False,
        }

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                results: list[RetrievedDocument] = []
                for item in data.get("results", []):
                    results.append(
                        RetrievedDocument(
                            id=str(uuid.uuid4()),
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            source_type="web_search",
                            content=item.get("content", ""),
                            retrieved_at="",
                            metadata={"query": query},
                        )
                    )
                return results
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    continue

        raise last_error  # type: ignore[misc]
