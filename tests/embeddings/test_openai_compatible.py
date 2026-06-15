from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.embeddings.openai_compatible import OpenAICompatibleEmbeddingClient


def _mock_http_response(embeddings: list[list[float]]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [{"embedding": e, "index": i} for i, e in enumerate(embeddings)],
        "model": "Qwen3-Embedding-4B",
        "usage": {"total_tokens": 100},
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestOpenAICompatibleEmbeddingClient:
    @pytest.fixture
    def client(self):
        return OpenAICompatibleEmbeddingClient(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="Qwen3-Embedding-4B",
            dim=4,
        )

    @pytest.mark.asyncio
    async def test_embed_returns_vectors(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response(
                [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
            )
            mock_cls.return_value = mock_client

            resp = await client.embed(["text a", "text b"])
            assert len(resp.embeddings) == 2
            assert resp.embeddings[0] == [0.1, 0.2, 0.3, 0.4]

    @pytest.mark.asyncio
    async def test_embed_uses_correct_url(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response([[0.1, 0.2, 0.3, 0.4]])
            mock_cls.return_value = mock_client

            await client.embed(["test"])
            url = mock_client.post.call_args.args[0]
            assert url == "https://api.example.com/v1/embeddings"

    @pytest.mark.asyncio
    async def test_embed_uses_bearer_auth(self, client):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response([[0.1, 0.2, 0.3, 0.4]])
            mock_cls.return_value = mock_client

            await client.embed(["test"])
            headers = mock_client.post.call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_embed_can_normalize_vectors(self):
        client = OpenAICompatibleEmbeddingClient(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="Qwen3-Embedding-4B",
            normalize=True,
        )
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = _mock_http_response([[3.0, 4.0]])
            mock_cls.return_value = mock_client

            resp = await client.embed(["test"])
            assert resp.embeddings[0] == [0.6, 0.8]
