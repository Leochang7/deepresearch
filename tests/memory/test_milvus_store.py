from unittest.mock import MagicMock, patch

import pytest

from deepresearch.memory.milvus_store import MilvusStore
from deepresearch.memory.store import MemoryEntry


def _mock_store():
    with patch("deepresearch.memory.milvus_store.MilvusClient") as mock_cls:
        client = MagicMock()
        client.has_collection.return_value = True
        client.describe_collection.return_value = {
            "description": (
                '{"schema_version": 1, "embedding_model": "", "dim": 1024}'
            ),
            "fields": [{"name": "embedding", "params": {"dim": 1024}}],
        }
        mock_cls.return_value = client
        store = MilvusStore()
        store.connect()
        yield store, client


@pytest.fixture
def store_and_client():
    yield from _mock_store()


@pytest.mark.asyncio
async def test_upsert_auto_connects_and_writes(store_and_client):
    store, client = store_and_client

    await store.upsert(
        [
            MemoryEntry(
                id="e1",
                run_id="r1",
                task_id="t1",
                title="Title",
                source_url="https://example.com",
                content="content",
                source_type="chunk",
                confidence=0.8,
                created_at="2026-06-15T00:00:00Z",
                metadata={"a": 1},
                embedding=[0.1] * 1024,
            )
        ]
    )

    client.upsert.assert_called_once()
    call = client.upsert.call_args
    assert call.kwargs["collection_name"] == "deepresearch_chunks"
    rows = call.kwargs["data"]
    assert len(rows) == 1
    assert rows[0]["id"] == "e1"
    assert rows[0]["title"] == "Title"
    assert rows[0]["source_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_search_builds_scalar_filters(store_and_client):
    store, client = store_and_client

    client.search.return_value = [
        [
            {
                "id": "e1",
                "distance": 0.91,
                "entity": {
                    "run_id": "r1",
                    "task_id": "t1",
                    "title": "Title",
                    "source_url": "https://example.com",
                    "content": "content",
                    "source_type": "chunk",
                    "confidence": 0.8,
                    "created_at": "2026-06-15T00:00:00Z",
                    "metadata_json": '{"a": 1}',
                    "embedding": [0.1] * 1024,
                },
            }
        ]
    ]

    results = await store.search(
        [0.1] * 1024,
        run_id="r1",
        task_id="t1",
        source_type="chunk",
        min_confidence=0.5,
        top_k=3,
    )

    call = client.search.call_args
    assert call.kwargs["limit"] == 3
    assert call.kwargs["filter"] == (
        'run_id == "r1" and task_id == "t1" and '
        'source_type == "chunk" and confidence >= 0.5'
    )
    assert results[0].entry.title == "Title"
    assert results[0].entry.source_url == "https://example.com"
    assert results[0].entry.metadata == {"a": 1}
    assert len(results[0].entry.embedding) == 1024


@pytest.mark.asyncio
async def test_keyword_search_queries_independent_candidates(store_and_client):
    store, client = store_and_client
    client.query.return_value = [
        {
            "id": "keyword-hit",
            "run_id": "r1",
            "task_id": "t1",
            "title": "Chinese source",
            "source_url": "",
            "content": "多智能体系统能够执行复杂研究任务",
            "source_type": "chunk",
            "confidence": 1.0,
            "created_at": "",
            "metadata_json": "{}",
            "embedding": [0.2] * 1024,
        },
        {
            "id": "other",
            "run_id": "r1",
            "task_id": "t1",
            "title": "Other",
            "source_url": "",
            "content": "unrelated",
            "source_type": "chunk",
            "confidence": 1.0,
            "created_at": "",
            "metadata_json": "{}",
            "embedding": [0.3] * 1024,
        },
    ]

    results = await store.keyword_search(
        "多智能体研究",
        run_id="r1",
        task_id="t1",
        source_type="chunk",
        top_k=5,
    )

    client.query.assert_called_once()
    assert [result.entry.id for result in results] == ["keyword-hit"]
    assert len(results[0].entry.embedding) == 1024


@pytest.mark.asyncio
async def test_delete_calls_both_collections(store_and_client):
    store, client = store_and_client

    await store.delete(["e1", "e2"])

    assert client.delete.call_count == 2


@pytest.mark.asyncio
async def test_snapshot_preserves_extended_fields(store_and_client):
    store, client = store_and_client

    client.query.return_value = [
        {
            "id": "e1",
            "run_id": "r1",
            "task_id": "t1",
            "title": "Title",
            "source_url": "https://example.com",
            "content": "content",
            "source_type": "chunk",
            "confidence": 0.8,
            "created_at": "2026-06-15T00:00:00Z",
            "metadata_json": '{"a": 1}',
        }
    ]

    entries = await store.snapshot("r1")

    assert len(entries) == 2
    assert entries[0].title == "Title"
    assert entries[0].source_url == "https://example.com"
    assert entries[0].metadata == {"a": 1}
