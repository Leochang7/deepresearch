from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from deepresearch.embeddings.base import EmbeddingClient, EmbeddingResponse
from deepresearch.llm.base import LLMClient, LLMMessage, LLMResponse
from deepresearch.rerankers.base import RerankerClient, RerankerResponse
from deepresearch.retrieval.base import Retriever
from deepresearch.schemas.evidence import RetrievedDocument


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class RunBudget:
    max_llm_calls: int = 80
    llm_calls: int = 0
    search_calls: int = 0
    fetched_docs: int = 0
    chunks: int = 0
    embedding_batches: int = 0
    rerank_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_seconds: float = 0.0
    _start_time: float = field(default_factory=time.monotonic, repr=False)

    def reserve_llm_call(self) -> None:
        if self.llm_calls >= self.max_llm_calls:
            raise BudgetExceededError(
                f"LLM call budget exhausted ({self.max_llm_calls} calls)"
            )
        self.llm_calls += 1

    def record_usage(self, usage: dict[str, int]) -> None:
        self.prompt_tokens += usage.get("prompt_tokens", usage.get("input_tokens", 0))
        self.completion_tokens += usage.get(
            "completion_tokens", usage.get("output_tokens", 0)
        )

    def finish(self) -> None:
        self.elapsed_seconds = time.monotonic() - self._start_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "llm_calls": self.llm_calls,
            "search_calls": self.search_calls,
            "fetched_docs": self.fetched_docs,
            "chunks": self.chunks,
            "embedding_batches": self.embedding_batches,
            "rerank_calls": self.rerank_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
        }


class BudgetedLLMClient(LLMClient):
    def __init__(self, delegate: LLMClient, budget: RunBudget) -> None:
        self._delegate = delegate
        self._budget = budget

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_completion_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self._budget.reserve_llm_call()
        response = await self._delegate.chat(
            messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_completion_tokens=max_completion_tokens,
            json_mode=json_mode,
        )
        self._budget.record_usage(response.usage)
        return response


class BudgetedRetriever(Retriever):
    def __init__(self, delegate: Retriever, budget: RunBudget) -> None:
        self._delegate = delegate
        self._budget = budget

    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str = "",
        task_id: str = "",
        top_k: int = 10,
    ) -> list[RetrievedDocument]:
        self._budget.search_calls += len(queries)
        return await self._delegate.retrieve(
            queries,
            run_id=run_id,
            task_id=task_id,
            top_k=top_k,
        )


class BudgetedEmbeddingClient(EmbeddingClient):
    def __init__(self, delegate: EmbeddingClient, budget: RunBudget) -> None:
        self._delegate = delegate
        self._budget = budget

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> EmbeddingResponse:
        self._budget.embedding_batches += 1
        response = await self._delegate.embed(texts, model=model)
        self._budget.record_usage(response.usage)
        return response


class BudgetedRerankerClient(RerankerClient):
    def __init__(self, delegate: RerankerClient, budget: RunBudget) -> None:
        self._delegate = delegate
        self._budget = budget

    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str | None = None,
        top_k: int | None = None,
    ) -> RerankerResponse:
        self._budget.rerank_calls += 1
        response = await self._delegate.rerank(
            query,
            documents,
            model=model,
            top_k=top_k,
        )
        self._budget.record_usage(response.usage)
        return response
