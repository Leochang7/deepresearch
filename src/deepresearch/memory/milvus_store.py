from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient

from deepresearch.memory.store import MemoryEntry, MemoryStore, SearchResult

_DIM = 1024
_METRIC = "COSINE"
_INDEX_TYPE = "HNSW"

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
        self._client: MilvusClient | None = None

    def connect(self) -> None:
        self._client = MilvusClient(uri=self._uri)
        self._ensure_collection(self._chunks_name)
        self._ensure_collection(self._memories_name)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _ensure_collection(self, name: str) -> None:
        assert self._client is not None
        if self._client.has_collection(name):
            self._validate_collection_schema(name)
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
        self._client.create_collection(
            collection_name=name,
            schema=schema,
        )
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type=_INDEX_TYPE,
            metric_type=_METRIC,
            params={"M": 16, "efConstruction": 256},
        )
        self._client.create_index(
            collection_name=name,
            index_params=index_params,
        )

    def _validate_collection_schema(self, name: str) -> None:
        assert self._client is not None
        schema = self._client.describe_collection(name)
        dim = _embedding_dim_from_schema(schema)
        if dim is not None and dim != self._dim:
            raise ValueError(
                f"Milvus collection {name} embedding dim mismatch: "
                f"expected {self._dim}, got {dim}"
            )

    def _ensure_connected(self) -> None:
        if self._client is None:
            self.connect()

    def _col_name(self, source_type: str) -> str:
        return self._chunks_name if source_type == "chunk" else self._memories_name

    async def upsert(self, entries: list[MemoryEntry]) -> None:
        if not entries:
            return
        self._ensure_connected()
        assert self._client is not None

        by_collection: dict[str, list[MemoryEntry]] = {}
        for entry in entries:
            col_name = self._col_name(entry.source_type)
            by_collection.setdefault(col_name, []).append(entry)

        for col_name, col_entries in by_collection.items():
            rows = [
                {
                    "id": e.id,
                    "run_id": e.run_id,
                    "task_id": e.task_id,
                    "title": e.title,
                    "source_url": e.source_url,
                    "content": e.content,
                    "source_type": e.source_type,
                    "confidence": e.confidence,
                    "created_at": e.created_at,
                    "metadata_json": json.dumps(e.metadata, ensure_ascii=False),
                    "embedding": e.embedding,
                }
                for e in col_entries
            ]
            self._client.upsert(collection_name=col_name, data=rows)

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
        assert self._client is not None

        col_name = self._col_name(source_type)
        self._client.load_collection(collection_name=col_name)

        filter_parts: list[str] = []
        if run_id:
            filter_parts.append(f'run_id == "{run_id}"')
        if task_id:
            filter_parts.append(f'task_id == "{task_id}"')
        if source_type:
            filter_parts.append(f'source_type == "{source_type}"')
        if min_confidence is not None:
            filter_parts.append(f"confidence >= {min_confidence}")
        filter_expr = " and ".join(filter_parts) if filter_parts else None

        results = self._client.search(
            collection_name=col_name,
            data=[query_embedding],
            anns_field="embedding",
            search_params={"metric_type": _METRIC, "params": {"ef": 128}},
            limit=top_k,
            filter=filter_expr,
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
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", {})
                entry = MemoryEntry(
                    id=hit.get("id", ""),
                    run_id=entity.get("run_id", ""),
                    task_id=entity.get("task_id", ""),
                    title=entity.get("title", ""),
                    source_url=entity.get("source_url", ""),
                    content=entity.get("content", ""),
                    source_type=entity.get("source_type", ""),
                    confidence=entity.get("confidence", 0.0),
                    created_at=entity.get("created_at", ""),
                    metadata=_loads_metadata(entity.get("metadata_json", "")),
                )
                search_results.append(
                    SearchResult(entry=entry, score=hit.get("distance", 0.0))
                )
        return search_results

    async def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        self._ensure_connected()
        assert self._client is not None
        for col_name in [self._chunks_name, self._memories_name]:
            self._client.delete(
                collection_name=col_name,
                ids=ids,
            )

    async def snapshot(self, run_id: str) -> list[MemoryEntry]:
        self._ensure_connected()
        assert self._client is not None
        entries: list[MemoryEntry] = []
        for col_name in [self._chunks_name, self._memories_name]:
            self._client.load_collection(collection_name=col_name)
            results = self._client.query(
                collection_name=col_name,
                filter=f'run_id == "{run_id}"',
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
                        id=r.get("id", ""),
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


def _embedding_dim_from_schema(schema: Any) -> int | None:
    fields = schema.get("fields", []) if isinstance(schema, dict) else []
    for schema_field in fields:
        if schema_field.get("name") != "embedding":
            continue
        params = schema_field.get("params") or schema_field.get("type_params") or {}
        dim = params.get("dim")
        return int(dim) if dim is not None else None
    return None
