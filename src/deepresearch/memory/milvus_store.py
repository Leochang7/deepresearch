from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from deepresearch.memory.store import MemoryEntry, MemoryStore, SearchResult

_DIM = 1024
_METRIC = "COSINE"
_INDEX = "HNSW"

_CHUNKS_COLLECTION = "deepresearch_chunks"
_MEMORIES_COLLECTION = "deepresearch_memories"


class MilvusStore(MemoryStore):
    def __init__(
        self,
        *,
        uri: str = "http://localhost:19530",
        chunks_collection: str = _CHUNKS_COLLECTION,
        memories_collection: str = _MEMORIES_COLLECTION,
        dim: int = _DIM,
    ) -> None:
        self._uri = uri
        self._chunks_name = chunks_collection
        self._memories_name = memories_collection
        self._dim = dim
        self._connected = False

    def connect(self) -> None:
        if "://" not in self._uri:
            Path(self._uri).expanduser().parent.mkdir(parents=True, exist_ok=True)
        connections.connect(alias="default", uri=self._uri)
        self._connected = True
        self._ensure_collection(self._chunks_name)
        self._ensure_collection(self._memories_name)

    def close(self) -> None:
        connections.disconnect("default")
        self._connected = False

    def _ensure_collection(self, name: str) -> None:
        if utility.has_collection(name):
            return

        fields = [
            FieldSchema(
                name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128
            ),
            FieldSchema(name="run_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="task_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="confidence", dtype=DataType.FLOAT),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self._dim,
            ),
        ]
        schema = CollectionSchema(fields=fields, description=f"DeepResearch {name}")
        col = Collection(name=name, schema=schema)
        col.create_index(
            field_name="embedding",
            index_params={
                "index_type": _INDEX,
                "metric_type": _METRIC,
                "params": {"M": 16, "efConstruction": 256},
            },
        )

    def _ensure_connected(self) -> None:
        if not self._connected:
            self.connect()

    def _get_collection(self, source_type: str) -> Collection:
        self._ensure_connected()
        if source_type == "chunk":
            return Collection(self._chunks_name)
        return Collection(self._memories_name)

    async def upsert(self, entries: list[MemoryEntry]) -> None:
        if not entries:
            return
        self._ensure_connected()

        by_collection: dict[str, list[MemoryEntry]] = {}
        for entry in entries:
            col_name = (
                self._chunks_name
                if entry.source_type == "chunk"
                else self._memories_name
            )
            by_collection.setdefault(col_name, []).append(entry)

        for col_name, col_entries in by_collection.items():
            col = Collection(col_name)
            ids = [e.id for e in col_entries]
            run_ids = [e.run_id for e in col_entries]
            task_ids = [e.task_id for e in col_entries]
            titles = [e.title for e in col_entries]
            source_urls = [e.source_url for e in col_entries]
            contents = [e.content for e in col_entries]
            source_types = [e.source_type for e in col_entries]
            confidences = [e.confidence for e in col_entries]
            created_ats = [e.created_at for e in col_entries]
            metadata_jsons = [
                json.dumps(e.metadata, ensure_ascii=False) for e in col_entries
            ]
            embeddings = [e.embedding for e in col_entries]

            col.upsert(
                [
                    ids,
                    run_ids,
                    task_ids,
                    titles,
                    source_urls,
                    contents,
                    source_types,
                    confidences,
                    created_ats,
                    metadata_jsons,
                    embeddings,
                ]
            )

    async def search(
        self,
        query_embedding: list[float],
        *,
        run_id: str = "",
        task_id: str = "",
        source_type: str = "",
        min_confidence: float | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        self._ensure_connected()
        col_name = self._chunks_name if source_type == "chunk" else self._memories_name
        col = Collection(col_name)
        col.load()

        filter_parts: list[str] = []
        if run_id:
            filter_parts.append(f'run_id == "{run_id}"')
        if task_id:
            filter_parts.append(f'task_id == "{task_id}"')
        if source_type:
            filter_parts.append(f'source_type == "{source_type}"')
        if min_confidence is not None:
            filter_parts.append(f"confidence >= {min_confidence}")
        expr = " and ".join(filter_parts) if filter_parts else ""

        results = col.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": _METRIC, "params": {"ef": 128}},
            limit=top_k,
            expr=expr or None,
            output_fields=[
                "run_id",
                "task_id",
                "title",
                "source_url",
                "content",
                "source_type",
                "confidence",
                "created_at",
                "metadata_json",
            ],
        )

        search_results: list[SearchResult] = []
        for hit in results[0]:
            entry = MemoryEntry(
                id=hit.id,
                run_id=hit.entity.get("run_id", ""),
                task_id=hit.entity.get("task_id", ""),
                title=hit.entity.get("title", ""),
                source_url=hit.entity.get("source_url", ""),
                content=hit.entity.get("content", ""),
                source_type=hit.entity.get("source_type", ""),
                confidence=hit.entity.get("confidence", 0.0),
                created_at=hit.entity.get("created_at", ""),
                metadata=_loads_metadata(hit.entity.get("metadata_json", "")),
            )
            search_results.append(SearchResult(entry=entry, score=hit.score))

        return search_results

    async def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self._ensure_connected()
        for col_name in [self._chunks_name, self._memories_name]:
            col = Collection(col_name)
            expr = f"id in {json.dumps(ids)}"
            col.delete(expr)

    async def snapshot(self, run_id: str) -> list[MemoryEntry]:
        self._ensure_connected()
        entries: list[MemoryEntry] = []
        for col_name in [self._chunks_name, self._memories_name]:
            col = Collection(col_name)
            col.load()
            results = col.query(
                expr=f'run_id == "{run_id}"',
                output_fields=[
                    "id",
                    "run_id",
                    "task_id",
                    "title",
                    "source_url",
                    "content",
                    "source_type",
                    "confidence",
                    "created_at",
                    "metadata_json",
                ],
            )
            for r in results:
                entries.append(
                    MemoryEntry(
                        id=r["id"],
                        run_id=r.get("run_id", ""),
                        task_id=r.get("task_id", ""),
                        title=r.get("title", ""),
                        source_url=r.get("source_url", ""),
                        content=r.get("content", ""),
                        source_type=r.get("source_type", ""),
                        confidence=r.get("confidence", 0.0),
                        created_at=r.get("created_at", ""),
                        metadata=_loads_metadata(r.get("metadata_json", "")),
                    )
                )
        return entries


async def export_snapshot(
    store: MemoryStore,
    run_id: str,
    output_path: Path | str,
) -> Path:
    entries = await store.snapshot(run_id)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for entry in entries:
            line = json.dumps(
                {
                    "id": entry.id,
                    "run_id": entry.run_id,
                    "task_id": entry.task_id,
                    "title": entry.title,
                    "source_url": entry.source_url,
                    "content": entry.content,
                    "source_type": entry.source_type,
                    "confidence": entry.confidence,
                    "created_at": entry.created_at,
                    "metadata": entry.metadata,
                },
                ensure_ascii=False,
            )
            f.write(line + "\n")
    return output


def _loads_metadata(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
