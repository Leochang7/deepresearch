from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> EmbeddingResponse: ...
