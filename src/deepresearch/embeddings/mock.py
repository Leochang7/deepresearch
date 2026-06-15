from __future__ import annotations

import hashlib

from deepresearch.embeddings.base import EmbeddingClient, EmbeddingResponse


class MockEmbeddingClient(EmbeddingClient):
    def __init__(self, dim: int = 1024) -> None:
        self._dim = dim

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> EmbeddingResponse:
        embeddings = [self._deterministic_vector(text) for text in texts]
        return EmbeddingResponse(
            embeddings=embeddings,
            model="mock-embedding",
            usage={"prompt_tokens": sum(len(t) for t in texts)},
        )

    def _deterministic_vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        raw = []
        for i in range(self._dim):
            byte_val = seed[i % len(seed)]
            raw.append((byte_val / 255.0) * 2 - 1)

        norm = sum(x * x for x in raw) ** 0.5
        if norm > 0:
            raw = [x / norm for x in raw]
        return raw
