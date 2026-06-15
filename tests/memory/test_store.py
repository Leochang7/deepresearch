import pytest

from deepresearch.memory.store import (
    MemoryEntry,
    MemoryStore,
    MockMemoryStore,
    SearchResult,
)


class TestMemoryStoreBase:
    def test_memory_store_is_abstract(self):
        with pytest.raises(TypeError):
            MemoryStore()


class TestMockMemoryStore:
    @pytest.fixture
    def store(self):
        return MockMemoryStore()

    @pytest.mark.asyncio
    async def test_upsert_and_count(self, store):
        entries = [
            MemoryEntry(id="e1", run_id="r1", content="hello"),
            MemoryEntry(id="e2", run_id="r1", content="world"),
        ]
        await store.upsert(entries)
        assert store.count == 2

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, store):
        await store.upsert([MemoryEntry(id="e1", content="old")])
        await store.upsert([MemoryEntry(id="e1", content="new")])
        assert store.count == 1

    @pytest.mark.asyncio
    async def test_search_returns_all(self, store):
        entries = [
            MemoryEntry(id="e1", run_id="r1", content="Python programming"),
            MemoryEntry(id="e2", run_id="r1", content="Java programming"),
        ]
        await store.upsert(entries)
        results = await store.search([0.1] * 1024, run_id="r1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_filters_by_run_id(self, store):
        await store.upsert(
            [
                MemoryEntry(id="e1", run_id="r1", content="a"),
                MemoryEntry(id="e2", run_id="r2", content="b"),
            ]
        )
        results = await store.search([0.1] * 1024, run_id="r1")
        assert len(results) == 1
        assert results[0].entry.id == "e1"

    @pytest.mark.asyncio
    async def test_search_filters_by_task_id(self, store):
        await store.upsert(
            [
                MemoryEntry(id="e1", run_id="r1", task_id="t1", content="a"),
                MemoryEntry(id="e2", run_id="r1", task_id="t2", content="b"),
            ]
        )
        results = await store.search([0.1] * 1024, task_id="t1")
        assert len(results) == 1
        assert results[0].entry.task_id == "t1"

    @pytest.mark.asyncio
    async def test_search_filters_by_source_type(self, store):
        await store.upsert(
            [
                MemoryEntry(id="e1", run_id="r1", source_type="chunk", content="a"),
                MemoryEntry(id="e2", run_id="r1", source_type="memory", content="b"),
            ]
        )
        results = await store.search([0.1] * 1024, source_type="chunk")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_filters_by_min_confidence(self, store):
        await store.upsert(
            [
                MemoryEntry(id="e1", run_id="r1", confidence=0.9, content="a"),
                MemoryEntry(id="e2", run_id="r1", confidence=0.3, content="b"),
            ]
        )
        results = await store.search([0.1] * 1024, min_confidence=0.5)
        assert len(results) == 1
        assert results[0].entry.id == "e1"

    @pytest.mark.asyncio
    async def test_search_top_k(self, store):
        for i in range(10):
            await store.upsert(
                [MemoryEntry(id=f"e{i}", run_id="r1", content=f"doc {i}")]
            )
        results = await store.search([0.1] * 1024, top_k=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_delete(self, store):
        await store.upsert(
            [
                MemoryEntry(id="e1", content="a"),
                MemoryEntry(id="e2", content="b"),
            ]
        )
        await store.delete(["e1"])
        assert store.count == 1

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self, store):
        await store.delete(["no-such-id"])
        assert store.count == 0

    @pytest.mark.asyncio
    async def test_snapshot_by_run_id(self, store):
        await store.upsert(
            [
                MemoryEntry(id="e1", run_id="r1", content="a"),
                MemoryEntry(id="e2", run_id="r2", content="b"),
                MemoryEntry(id="e3", run_id="r1", content="c"),
            ]
        )
        entries = await store.snapshot("r1")
        assert len(entries) == 2
        assert all(e.run_id == "r1" for e in entries)

    @pytest.mark.asyncio
    async def test_search_cosine_similarity(self, store):
        v1 = [1.0] + [0.0] * 1023
        v2 = [0.0, 1.0] + [0.0] * 1022
        await store.upsert(
            [
                MemoryEntry(id="e1", run_id="r1", embedding=v1, content="a"),
                MemoryEntry(id="e2", run_id="r1", embedding=v2, content="b"),
            ]
        )
        results = await store.search(v1, run_id="r1")
        assert results[0].entry.id == "e1"
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_search_result_has_score(self, store):
        await store.upsert([MemoryEntry(id="e1", run_id="r1", content="a")])
        results = await store.search([0.1] * 1024)
        assert isinstance(results[0], SearchResult)
        assert isinstance(results[0].score, float)
