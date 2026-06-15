import pytest

from deepresearch.rerankers.base import RerankerClient
from deepresearch.rerankers.mock import MockRerankerClient


class TestRerankerBase:
    def test_reranker_client_is_abstract(self):
        with pytest.raises(TypeError):
            RerankerClient()


class TestMockRerankerClient:
    @pytest.fixture
    def client(self):
        return MockRerankerClient()

    @pytest.mark.asyncio
    async def test_rerank_returns_results(self, client):
        docs = ["Python is great", "Java is popular", "Rust is fast"]
        resp = await client.rerank("Python programming", docs)
        assert len(resp.results) == 3
        assert all(hasattr(r, "index") and hasattr(r, "score") for r in resp.results)

    @pytest.mark.asyncio
    async def test_rerank_relevant_first(self, client):
        docs = ["Python is a programming language", "The weather is nice today"]
        resp = await client.rerank("Python programming", docs)
        assert resp.results[0].index == 0

    @pytest.mark.asyncio
    async def test_rerank_top_k(self, client):
        docs = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        resp = await client.rerank("query", docs, top_k=2)
        assert len(resp.results) == 2

    @pytest.mark.asyncio
    async def test_rerank_scores_ordered(self, client):
        docs = ["Python programming tutorial", "Cooking recipe", "Python docs"]
        resp = await client.rerank("Python programming", docs)
        scores = [r.score for r in resp.results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_rerank_preserves_text(self, client):
        docs = ["hello world", "foo bar"]
        resp = await client.rerank("query", docs)
        texts = {r.text for r in resp.results}
        assert texts == {"hello world", "foo bar"}
