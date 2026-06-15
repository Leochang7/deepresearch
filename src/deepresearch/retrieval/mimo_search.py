from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from deepresearch.retrieval.base import Retriever
from deepresearch.schemas.evidence import RetrievedDocument


class MiMoSearchRetriever(Retriever):
    def __init__(
        self,
        *,
        base_url: str = "https://api.xiaomimimo.com/v1",
        api_key: str = "",
        model: str = "mimo-v2.5-pro",
        max_keyword: int = 3,
        force_search: bool = True,
        limit: int = 5,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_keyword = max_keyword
        self._force_search = force_search
        self._limit = limit
        self._timeout = timeout

    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str = "",
        task_id: str = "",
        top_k: int = 10,
    ) -> list[RetrievedDocument]:
        all_docs: list[RetrievedDocument] = []
        for query in queries:
            docs = await self._search(query)
            all_docs.extend(docs)
        return all_docs[:top_k]

    async def _search(self, query: str) -> list[RetrievedDocument]:
        url = f"{self._base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": query}],
            "tools": [
                {
                    "type": "web_search",
                    "max_keyword": self._max_keyword,
                    "force_search": self._force_search,
                    "limit": self._limit,
                }
            ],
        }
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results: list[RetrievedDocument] = []
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "")

        tool_calls = message.get("tool_calls", [])
        for tc in tool_calls:
            fn = tc.get("function", {})
            if fn.get("name") == "web_search":
                try:
                    search_data = json.loads(fn.get("arguments", "{}"))
                    for item in search_data.get("results", []):
                        results.append(
                            RetrievedDocument(
                                id=str(uuid.uuid4()),
                                title=item.get("title", ""),
                                url=item.get("url", ""),
                                source_type="mimo_search",
                                content=item.get("content", item.get("snippet", "")),
                                metadata={"query": query},
                            )
                        )
                except (json.JSONDecodeError, KeyError):
                    pass

        if not results and content:
            results.append(
                RetrievedDocument(
                    id=str(uuid.uuid4()),
                    title=f"MiMo search: {query}",
                    content=content,
                    source_type="mimo_search",
                    metadata={"query": query},
                )
            )

        return results[: self._limit]
