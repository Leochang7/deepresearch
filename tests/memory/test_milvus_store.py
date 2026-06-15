from unittest.mock import MagicMock, patch

import pytest

from deepresearch.memory.milvus_store import MilvusLiteStore
from deepresearch.memory.store import MemoryEntry


@pytest.fixture
def milvus_patches():
    with (
        patch("deepresearch.memory.milvus_store.connections") as connections,
        patch("deepresearch.memory.milvus_store.utility") as utility,
        patch("deepresearch.memory.milvus_store.Collection") as collection,
    ):
        utility.has_collection.return_value = True
        yield connections, utility, collection


@pytest.mark.asyncio
async def test_upsert_auto_connects_and_writes_extended_fields(milvus_patches):
    connections, _, collection = milvus_patches
    col = MagicMock()
    collection.return_value = col
    store = MilvusLiteStore(uri="./data/test.db")

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

    connections.connect.assert_called_once()
    col.upsert.assert_called_once()
    rows = col.upsert.call_args.args[0]
    assert rows[0] == ["e1"]
    assert rows[3] == ["Title"]
    assert rows[4] == ["https://example.com"]
    assert rows[8] == ["2026-06-15T00:00:00Z"]
    assert rows[9] == ['{"a": 1}']


@pytest.mark.asyncio
async def test_search_builds_scalar_filters(milvus_patches):
    _, _, collection = milvus_patches
    col = MagicMock()
    hit = MagicMock()
    hit.id = "e1"
    hit.score = 0.91
    hit.entity.get.side_effect = lambda key, default=None: {
        "run_id": "r1",
        "task_id": "t1",
        "title": "Title",
        "source_url": "https://example.com",
        "content": "content",
        "source_type": "chunk",
        "confidence": 0.8,
        "created_at": "2026-06-15T00:00:00Z",
        "metadata_json": '{"a": 1}',
    }.get(key, default)
    col.search.return_value = [[hit]]
    collection.return_value = col

    store = MilvusLiteStore(uri="./data/test.db")
    results = await store.search(
        [0.1] * 1024,
        run_id="r1",
        task_id="t1",
        source_type="chunk",
        min_confidence=0.5,
        top_k=3,
    )

    _, kwargs = col.search.call_args
    assert kwargs["limit"] == 3
    assert kwargs["expr"] == (
        'run_id == "r1" and task_id == "t1" and '
        'source_type == "chunk" and confidence >= 0.5'
    )
    assert results[0].entry.title == "Title"
    assert results[0].entry.source_url == "https://example.com"
    assert results[0].entry.metadata == {"a": 1}


@pytest.mark.asyncio
async def test_delete_auto_connects_and_deletes_both_collections(milvus_patches):
    connections, _, collection = milvus_patches
    col = MagicMock()
    collection.return_value = col
    store = MilvusLiteStore(uri="./data/test.db")

    await store.delete(["e1", "e2"])

    connections.connect.assert_called_once()
    assert col.delete.call_count == 2
    assert col.delete.call_args.args[0] == 'id in ["e1", "e2"]'


@pytest.mark.asyncio
async def test_snapshot_preserves_extended_fields(milvus_patches):
    _, _, collection = milvus_patches
    col = MagicMock()
    col.query.return_value = [
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
    collection.return_value = col
    store = MilvusLiteStore(uri="./data/test.db")

    entries = await store.snapshot("r1")

    assert len(entries) == 2
    assert entries[0].title == "Title"
    assert entries[0].source_url == "https://example.com"
    assert entries[0].metadata == {"a": 1}
