import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from deepresearch.llm.openai_compatible import OpenAICompatibleLLMClient


def test_constructor_defaults():
    client = OpenAICompatibleLLMClient(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        model="gpt-4",
    )
    assert client._model == "gpt-4"


@pytest.mark.asyncio
async def test_chat_sends_bearer_auth():
    client = OpenAICompatibleLLMClient(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        model="gpt-4",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello"}}],
        "model": "gpt-4",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        result = await client.chat([{"role": "user", "content": "Hi"}])
        assert result.content == "Hello"


@pytest.mark.asyncio
async def test_chat_custom_header():
    client = OpenAICompatibleLLMClient(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        model="gpt-4",
        api_key_header="api-key",
        api_key_prefix="",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello"}}],
        "model": "gpt-4",
        "usage": {},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        await client.chat([{"role": "user", "content": "Hi"}])
        headers = mock_post.call_args.kwargs.get("headers", {})
        assert headers.get("api-key") == "test-key"


@pytest.mark.asyncio
async def test_chat_max_tokens_field():
    client = OpenAICompatibleLLMClient(
        base_url="https://api.example.com/v1",
        api_key="key",
        model="m",
        max_tokens_field="max_completion_tokens",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "R"}}],
        "model": "m",
        "usage": {},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
        await client.chat([{"role": "user", "content": "Hi"}], max_completion_tokens=100)
        body = mock_post.call_args.kwargs.get("json", {})
        assert body.get("max_completion_tokens") == 100
