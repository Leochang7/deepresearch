from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.llm.base import LLMMessage
from deepresearch.llm.mimo import MiMoLLMClient


def _mock_http_response(content: str, model: str = "mimo-v2.5-pro") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}, "index": 0}],
        "model": model,
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestMiMoLLMClient:
    @pytest.fixture
    def client(self):
        return MiMoLLMClient(api_key="test-key", model="mimo-v2.5-pro")

    @pytest.mark.asyncio
    async def test_chat_sends_correct_payload(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("hello")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages, temperature=0.5, top_p=0.9)

            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["model"] == "mimo-v2.5-pro"
            assert payload["temperature"] == 0.5
            assert payload["top_p"] == 0.9
            assert payload["thinking"] == {"type": "disabled"}

    @pytest.mark.asyncio
    async def test_chat_preserves_zero_values(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("hello")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages, temperature=0.0, top_p=0.0)

            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["temperature"] == 0.0
            assert payload["top_p"] == 0.0

    @pytest.mark.asyncio
    async def test_chat_uses_api_key_header(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages)

            headers = mock_client.post.call_args.kwargs["headers"]
            assert headers["api-key"] == "test-key"
            assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_chat_returns_response(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("result text")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            resp = await client.chat(messages)

            assert resp.content == "result text"
            assert resp.model == "mimo-v2.5-pro"
            assert resp.usage["prompt_tokens"] == 100

    @pytest.mark.asyncio
    async def test_chat_json_mode(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("{}")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages, json_mode=True)

            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_chat_max_completion_tokens(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages, max_completion_tokens=2048)

            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["max_completion_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_url_construction(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages)

            url = mock_client.post.call_args.args[0]
            assert url == "https://api.xiaomimimo.com/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_default_params(self):
        client = MiMoLLMClient(
            api_key="key",
            default_temperature=0.7,
            default_top_p=0.95,
            default_max_completion_tokens=512,
        )
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response("ok")
            mock_cls.return_value = mock_client

            messages = [LLMMessage(role="user", content="test")]
            await client.chat(messages)

            payload = mock_client.post.call_args.kwargs["json"]
            assert payload["temperature"] == 0.7
            assert payload["max_completion_tokens"] == 512
