from __future__ import annotations

from abc import ABC, abstractmethod

from deepresearch.schemas.evidence import RetrievedDocument


class Retriever(ABC):
    @abstractmethod
    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str = "",
        task_id: str = "",
        top_k: int = 10,
    ) -> list[RetrievedDocument]: ...
