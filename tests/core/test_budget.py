import time
from unittest.mock import AsyncMock

import pytest

from deepresearch.core.budget import (
    BudgetedEmbeddingClient,
    BudgetedLLMClient,
    BudgetedRerankerClient,
    BudgetedRetriever,
    BudgetExceededError,
    RunBudget,
)
from deepresearch.embeddings.base import EmbeddingResponse
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.llm.base import LLMMessage
from deepresearch.llm.mock import MockLLM
from deepresearch.rerankers.base import RerankerResponse
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.mock import MockRetriever


def test_budget_counts_increment():
    b = RunBudget()
    b.llm_calls += 3
    b.search_calls += 5
    b.fetched_docs += 10
    b.chunks += 40
    b.embedding_batches += 2
    b.rerank_calls += 1
    assert b.llm_calls == 3
    assert b.search_calls == 5
    assert b.fetched_docs == 10
    assert b.chunks == 40
    assert b.embedding_batches == 2
    assert b.rerank_calls == 1


def test_budget_finish_records_elapsed():
    b = RunBudget()
    time.sleep(0.05)
    b.finish()
    assert b.elapsed_seconds >= 0.04
    assert b.elapsed_seconds < 1.0


def test_budget_to_dict():
    b = RunBudget()
    b.llm_calls = 2
    b.search_calls = 4
    b.fetched_docs = 6
    b.chunks = 24
    b.embedding_batches = 1
    b.rerank_calls = 1
    b.finish()
    d = b.to_dict()
    assert d["llm_calls"] == 2
    assert d["search_calls"] == 4
    assert d["elapsed_seconds"] >= 0
    assert isinstance(d["elapsed_seconds"], float)
    assert "_start_time" not in d


@pytest.mark.asyncio
async def test_budgeted_llm_enforces_limit_and_counts_tokens():
    llm = MockLLM(responses=["first"])
    budget = RunBudget(max_llm_calls=1)
    client = BudgetedLLMClient(llm, budget)

    await client.chat([LLMMessage(role="user", content="hello")])

    assert budget.llm_calls == 1
    assert budget.prompt_tokens == 100
    assert budget.completion_tokens == 50
    with pytest.raises(BudgetExceededError, match="budget exhausted"):
        await client.chat([LLMMessage(role="user", content="again")])


@pytest.mark.asyncio
async def test_budgeted_clients_count_actual_calls_and_usage():
    budget = RunBudget()
    embedding = MockEmbeddingClient()
    reranker = MockRerankerClient()
    embedding.embed = AsyncMock(  # type: ignore[method-assign]
        return_value=EmbeddingResponse(
            embeddings=[[1.0]],
            usage={"prompt_tokens": 4},
        )
    )
    reranker.rerank = AsyncMock(  # type: ignore[method-assign]
        return_value=RerankerResponse(
            results=[],
            usage={"input_tokens": 5},
        )
    )

    await BudgetedRetriever(MockRetriever(), budget).retrieve(["query", "alternate"])
    await BudgetedEmbeddingClient(embedding, budget).embed(["text"])
    await BudgetedRerankerClient(reranker, budget).rerank("query", ["doc"])

    assert budget.search_calls == 2
    assert budget.embedding_batches == 1
    assert budget.rerank_calls == 1
    assert budget.prompt_tokens == 9
