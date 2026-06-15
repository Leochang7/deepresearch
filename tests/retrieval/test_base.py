import pytest

from deepresearch.retrieval.base import Retriever
from deepresearch.retrieval.mock import MockRetriever
from deepresearch.schemas.evidence import RetrievedDocument


class TestRetrieverBase:
    def test_retriever_is_abstract(self):
        with pytest.raises(TypeError):
            Retriever()


class TestMockRetriever:
    @pytest.mark.asyncio
    async def test_returns_docs_from_constructor(self):
        docs = [
            RetrievedDocument(id="d1", title="Doc 1", content="content 1"),
            RetrievedDocument(id="d2", title="Doc 2", content="content 2"),
        ]
        retriever = MockRetriever(docs=docs)
        results = await retriever.retrieve(["query"])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_returns_mock_when_no_docs(self):
        retriever = MockRetriever()
        results = await retriever.retrieve(["test query"])
        assert len(results) >= 1
        assert "test query" in results[0].content

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self):
        docs = [
            RetrievedDocument(id=f"d{i}", title=f"Doc {i}", content=f"content {i}")
            for i in range(10)
        ]
        retriever = MockRetriever(docs=docs)
        results = await retriever.retrieve(["query"], top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_tracks_calls(self):
        retriever = MockRetriever()
        await retriever.retrieve(["q1", "q2"], run_id="r1", task_id="t1", top_k=5)
        assert len(retriever.calls) == 1
        assert retriever.calls[0]["queries"] == ["q1", "q2"]
        assert retriever.calls[0]["run_id"] == "r1"
