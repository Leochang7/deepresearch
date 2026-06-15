from __future__ import annotations

from typing import Any

import httpx

from deepresearch.rerankers.base import (
    RerankerClient,
    RerankerResponse,
    RerankResult,
)


class OpenAICompatibleRerankerClient(RerankerClient):
    def __init__(
        self,
        *,
        base_url: str = "",
        api_key: str = "",
        model: str = "bge-reranker-v2-m32",
        batch_size: int = 16,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._batch_size = batch_size
        self._timeout = timeout
        self._max_retries = max_retries

    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str | None = None,
        top_k: int | None = None,
    ) -> RerankerResponse:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "query": query,
            "documents": documents,
        }
        if top_k is not None:
            payload["top_n"] = top_k

        url = f"{self._base_url}/rerank"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                results = []
                for item in data.get("results", []):
                    results.append(
                        RerankResult(
                            index=item["index"],
                            score=item["relevance_score"],
                            text=documents[item["index"]]
                            if item["index"] < len(documents)
                            else "",
                        )
                    )

                usage = data.get("usage", {})
                return RerankerResponse(
                    results=results,
                    model=data.get("model", model or self._model),
                    usage={
                        "prompt_tokens": usage.get("total_tokens", 0),
                    },
                )
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    continue

        raise last_error  # type: ignore[misc]
