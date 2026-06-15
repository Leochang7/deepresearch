from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.llm.base import LLMMessage
from deepresearch.llm.deepseek import DeepSeekLLMClient


def _mock_http_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}, "index": 0}],
        "model": "deepseek-chat",
        "usage": {"prompt_tokens": 80, "completion_tokens": 40},
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestDeepSeekLLMClient:
    @pytest.fixture
    def client(self):
        return DeepSeekLLMClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_uses_bearer_auth(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            await client.chat([LLMMessage(role="user", content="hi")])
            headers = mock_client.post.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_uses_max_tokens_field(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            await client.chat(
                [LLMMessage(role="user", content="hi")], max_completion_tokens=512
            )
            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_preserves_zero_values(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            await client.chat(
                [LLMMessage(role="user", content="hi")],
                temperature=0.0,
                top_p=0.0,
            )
            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["temperature"] == 0.0
            assert payload["top_p"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_response(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("result")
            mock_cls.return_value = mock_client

            resp = await client.chat([LLMMessage(role="user", content="test")])
            assert resp.content == "result"
            assert resp.model == "deepseek-chat"
