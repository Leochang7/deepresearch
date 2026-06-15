from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.retrieval.tavily_search import TavilyWebSearchRetriever


def _mock_tavily_response(results: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"results": results}
    resp.raise_for_status = MagicMock()
    return resp


class TestTavilyWebSearchRetriever:
    @pytest.fixture
    def retriever(self):
        return TavilyWebSearchRetriever(api_key="test-key", max_retries=0)

    @pytest.mark.asyncio
    async def test_returns_documents(self, retriever):
        api_results = [
            {"title": "Doc 1", "url": "http://a.com", "content": "content 1"},
            {"title": "Doc 2", "url": "http://b.com", "content": "content 2"},
        ]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_tavily_response(api_results)
            mock_cls.return_value = mock_client

            results = await retriever.retrieve(["test query"])
            assert len(results) == 2
            assert results[0].title == "Doc 1"
            assert results[0].source_type == "web_search"

    @pytest.mark.asyncio
    async def test_sends_api_key(self, retriever):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_tavily_response([])
            mock_cls.return_value = mock_client

            await retriever.retrieve(["query"])
            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["api_key"] == "test-key"
            assert payload["query"] == "query"

    @pytest.mark.asyncio
    async def test_multiple_queries(self, retriever):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_tavily_response(
                [{"title": "t", "url": "u", "content": "c"}]
            )
            mock_cls.return_value = mock_client

            await retriever.retrieve(["q1", "q2"], top_k=10)
            assert mock_client.post.call_count == 2
