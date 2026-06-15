from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RerankResult:
    index: int
    score: float
    text: str = ""


@dataclass
class RerankerResponse:
    results: list[RerankResult]
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class RerankerClient(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str | None = None,
        top_k: int | None = None,
    ) -> RerankerResponse: ...
