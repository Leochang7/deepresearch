from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.rerankers.openai_compatible import OpenAICompatibleRerankerClient


def _mock_http_response(results: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "results": results,
        "model": "bge-reranker-v2-m32",
        "usage": {"total_tokens": 50},
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestOpenAICompatibleRerankerClient:
    @pytest.fixture
    def client(self):
        return OpenAICompatibleRerankerClient(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="bge-reranker-v2-m32",
        )

    @pytest.mark.asyncio
    async def test_rerank_returns_sorted_results(self, client):
        docs = ["doc about Python", "doc about cooking", "doc about programming"]
        api_results = [
            {"index": 0, "relevance_score": 0.95},
            {"index": 2, "relevance_score": 0.80},
            {"index": 1, "relevance_score": 0.10},
        ]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response(api_results)
            mock_cls.return_value = mock_client

            resp = await client.rerank("Python programming", docs)
            assert len(resp.results) == 3
            assert resp.results[0].score == 0.95
            assert resp.results[0].text == "doc about Python"

    @pytest.mark.asyncio
    async def test_rerank_uses_correct_url(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response([])
            mock_cls.return_value = mock_client

            await client.rerank("query", ["doc"])
            url = mock_client.post.call_args.args[0]
            assert url == "https://api.example.com/v1/rerank"

    @pytest.mark.asyncio
    async def test_rerank_sends_top_k(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response([])
            mock_cls.return_value = mock_client

            await client.rerank("query", ["a", "b", "c"], top_k=2)
            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["top_n"] == 2
