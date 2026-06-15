import pytest

from deepresearch.embeddings.base import EmbeddingClient, EmbeddingResponse
from deepresearch.embeddings.mock import MockEmbeddingClient


class TestEmbeddingBase:
    def test_embedding_client_is_abstract(self):
        with pytest.raises(TypeError):
            EmbeddingClient()

    def test_embedding_response(self):
        resp = EmbeddingResponse(embeddings=[[0.1, 0.2]], model="test")
        assert len(resp.embeddings) == 1


class TestMockEmbeddingClient:
    @pytest.fixture
    def client(self):
        return MockEmbeddingClient(dim=1024)

    @pytest.mark.asyncio
    async def test_embed_single(self, client):
        resp = await client.embed(["hello world"])
        assert len(resp.embeddings) == 1
        assert len(resp.embeddings[0]) == 1024

    @pytest.mark.asyncio
    async def test_embed_batch(self, client):
        resp = await client.embed(["text a", "text b", "text c"])
        assert len(resp.embeddings) == 3

    @pytest.mark.asyncio
    async def test_deterministic(self, client):
        r1 = await client.embed(["same text"])
        r2 = await client.embed(["same text"])
        assert r1.embeddings[0] == r2.embeddings[0]

    @pytest.mark.asyncio
    async def test_different_inputs_differ(self, client):
        r1 = await client.embed(["text alpha"])
        r2 = await client.embed(["text beta"])
        assert r1.embeddings[0] != r2.embeddings[0]

    @pytest.mark.asyncio
    async def test_custom_dim(self):
        client = MockEmbeddingClient(dim=512)
        resp = await client.embed(["test"])
        assert len(resp.embeddings[0]) == 512
