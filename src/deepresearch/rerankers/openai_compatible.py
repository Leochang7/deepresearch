from __future__ import annotations

from typing import Any

from deepresearch.llm.http import auth_headers, post_json
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
        data = await post_json(
            url,
            payload=payload,
            headers=auth_headers(api_key=self._api_key),
            timeout=self._timeout,
            max_retries=self._max_retries,
        )

        results = []
        for item in data.get("results", []):
            index = item["index"]
            results.append(
                RerankResult(
                    index=index,
                    score=item["relevance_score"],
                    text=documents[index] if index < len(documents) else "",
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
