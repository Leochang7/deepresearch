from __future__ import annotations

from typing import Any

import httpx

from deepresearch.embeddings.base import EmbeddingClient, EmbeddingResponse


class OpenAICompatibleEmbeddingClient(EmbeddingClient):
    def __init__(
        self,
        *,
        base_url: str = "",
        api_key: str = "",
        model: str = "Qwen3-Embedding-4B",
        dim: int = 1024,
        batch_size: int = 32,
        timeout: float = 60.0,
        max_retries: int = 2,
        normalize: bool = False,
        request_dimensions: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dim = dim
        self._batch_size = batch_size
        self._timeout = timeout
        self._max_retries = max_retries
        self._normalize = normalize
        self._request_dimensions = request_dimensions

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> EmbeddingResponse:
        all_embeddings: list[list[float]] = []
        total_tokens = 0

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_result = await self._embed_batch(batch, model)
            all_embeddings.extend(batch_result.embeddings)
            total_tokens += batch_result.usage.get("prompt_tokens", 0)

        return EmbeddingResponse(
            embeddings=all_embeddings,
            model=model or self._model,
            usage={"prompt_tokens": total_tokens},
        )

    async def _embed_batch(
        self,
        texts: list[str],
        model: str | None,
    ) -> EmbeddingResponse:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "input": texts,
        }
        if self._request_dimensions:
            payload["dimensions"] = self._dim
        url = f"{self._base_url}/embeddings"
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

                embeddings = [item["embedding"] for item in data["data"]]
                invalid_dims = sorted({len(embedding) for embedding in embeddings})
                if invalid_dims != [self._dim]:
                    raise ValueError(
                        "Embedding response dimensions do not match configured "
                        f"dim={self._dim}: got {invalid_dims}"
                    )
                if self._normalize:
                    embeddings = [_l2_normalize(embedding) for embedding in embeddings]
                usage = data.get("usage", {})

                return EmbeddingResponse(
                    embeddings=embeddings,
                    model=data.get("model", model or self._model),
                    usage={"prompt_tokens": usage.get("total_tokens", 0)},
                )
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    continue

        raise last_error  # type: ignore[misc]


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = sum(x * x for x in vector) ** 0.5
    if norm == 0:
        return vector
    return [x / norm for x in vector]
