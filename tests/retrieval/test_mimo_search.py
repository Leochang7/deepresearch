import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.retrieval.mimo_search import MiMoSearchRetriever


def _mock_mimo_response(content: str, tool_calls: list | None = None) -> MagicMock:
    message: dict = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": message}],
        "model": "mimo-v2.5-pro",
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestMiMoSearchRetriever:
    @pytest.fixture
    def retriever(self):
        return MiMoSearchRetriever(api_key="test-key")

    @pytest.mark.asyncio
    async def test_returns_content_when_no_tool_calls(self, retriever):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_mimo_response("Some answer")
            mock_cls.return_value = mock_client

            results = await retriever.retrieve(["test"])
            assert len(results) == 1
            assert results[0].content == "Some answer"
            assert results[0].source_type == "mimo_search"

    @pytest.mark.asyncio
    async def test_parses_tool_calls(self, retriever):
        search_results = {
            "results": [
                {"title": "Paper 1", "url": "http://a.com", "content": "Abstract 1"},
                {"title": "Paper 2", "url": "http://b.com", "content": "Abstract 2"},
            ]
        }
        tool_calls = [
            {
                "function": {
                    "name": "web_search",
                    "arguments": json.dumps(search_results),
                }
            }
        ]
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_mimo_response("", tool_calls)
            mock_cls.return_value = mock_client

            results = await retriever.retrieve(["test"])
            assert len(results) == 2
            assert results[0].title == "Paper 1"

    @pytest.mark.asyncio
    async def test_uses_api_key_header(self, retriever):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_mimo_response("ok")
            mock_cls.return_value = mock_client

            await retriever.retrieve(["test"])
            headers = mock_client.post.call_args.kwargs["headers"]
            assert headers["api-key"] == "test-key"

    @pytest.mark.asyncio
    async def test_sends_flat_web_search_tool_payload(self, retriever):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_mimo_response("ok")
            mock_cls.return_value = mock_client

            await retriever.retrieve(["test"])
            payload = mock_client.post.call_args.kwargs["json"]
            tool = payload["tools"][0]
            assert tool == {
                "type": "web_search",
                "max_keyword": 3,
                "force_search": True,
                "limit": 5,
            }
            assert "web_search" not in tool
