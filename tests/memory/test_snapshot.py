import json

import pytest

from deepresearch.memory.milvus_store import export_snapshot
from deepresearch.memory.store import MemoryEntry, MockMemoryStore


class TestExportSnapshot:
    @pytest.mark.asyncio
    async def test_exports_jsonl(self, tmp_path):
        store = MockMemoryStore()
        await store.upsert(
            [
                MemoryEntry(
                    id="e1",
                    run_id="r1",
                    task_id="t1",
                    title="Title 1",
                    source_url="https://example.com/1",
                    content="hello",
                    source_type="chunk",
                    confidence=0.9,
                    created_at="2026-06-15T00:00:00Z",
                    metadata={"source": "test"},
                ),
                MemoryEntry(
                    id="e2",
                    run_id="r1",
                    task_id="t2",
                    content="world",
                    source_type="memory",
                    confidence=0.8,
                ),
                MemoryEntry(
                    id="e3",
                    run_id="r2",
                    task_id="t1",
                    content="other",
                    source_type="chunk",
                ),
            ]
        )

        output = await export_snapshot(store, "r1", tmp_path / "snapshot.jsonl")
        assert output.exists()

        lines = output.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        assert entry1["run_id"] == "r1"
        assert entry1["id"] in ("e1", "e2")
        if entry1["id"] == "e1":
            assert entry1["title"] == "Title 1"
            assert entry1["source_url"] == "https://example.com/1"
            assert entry1["created_at"] == "2026-06-15T00:00:00Z"
            assert entry1["metadata"] == {"source": "test"}

    @pytest.mark.asyncio
    async def test_creates_parent_dir(self, tmp_path):
        store = MockMemoryStore()
        await store.upsert([MemoryEntry(id="e1", run_id="r1", content="test")])

        output = await export_snapshot(
            store, "r1", tmp_path / "deep" / "dir" / "snap.jsonl"
        )
        assert output.exists()

    @pytest.mark.asyncio
    async def test_empty_run_returns_empty_file(self, tmp_path):
        store = MockMemoryStore()
        output = await export_snapshot(store, "no-such-run", tmp_path / "empty.jsonl")
        assert output.exists()
        assert output.read_text(encoding="utf-8").strip() == ""
