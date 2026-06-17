from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient

from deepresearch.memory.store import (
    MemoryEntry,
    MemoryStore,
    SearchResult,
)
from deepresearch.retrieval.lexical import lexical_score

_DIM = 1024
_METRIC = "COSINE"
_INDEX_TYPE = "HNSW"
_SCHEMA_VERSION = 1

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
        embedding_model: str = "",
    ) -> None:
        self._uri = uri
        self._chunks_name = chunks_collection
        self._memories_name = memories_collection
        self._dim = dim
        self._embedding_model = embedding_model
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
        schema = CollectionSchema(
            fields=fields,
            description=self._schema_description(),
        )
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
        meta = self._collection_metadata(schema)
        if meta is None:
            raise ValueError(
                f"Milvus collection {name} has no DeepResearch schema metadata; "
                "recreate the collection before use"
            )
        if meta.get("schema_version") != _SCHEMA_VERSION:
            raise ValueError(
                f"Milvus collection {name} schema version mismatch: "
                f"expected {_SCHEMA_VERSION}, got {meta.get('schema_version')}"
            )
        if meta.get("dim") != self._dim:
            raise ValueError(
                f"Milvus collection {name} metadata dim mismatch: "
                f"expected {self._dim}, got {meta.get('dim')}"
            )
        stored_model = meta.get("embedding_model", "")
        if self._embedding_model and stored_model != self._embedding_model:
            raise ValueError(
                f"Milvus collection {name} embedding model mismatch: "
                f"expected {self._embedding_model}, got {stored_model or '<missing>'}"
            )

    def _schema_description(self) -> str:
        return json.dumps(
            {
                "schema_version": _SCHEMA_VERSION,
                "embedding_model": self._embedding_model,
                "dim": self._dim,
            }
        )

    @staticmethod
    def _collection_metadata(schema: dict) -> dict | None:
        desc = schema.get("description", "")
        if not desc:
            return None
        try:
            data = json.loads(desc)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError):
            return None

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
            rows = [_entry_to_row(entry) for entry in col_entries]
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

        filter_expr = _build_filter_expr(
            run_id=run_id,
            task_id=task_id,
            source_type=source_type,
            min_confidence=min_confidence,
        )

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
                "embedding",
            ],
        )

        search_results: list[SearchResult] = []
        for hits in results:
            for hit in hits:
                entry = _entry_from_row(hit.get("entity", {}), id_=hit.get("id", ""))
                search_results.append(
                    SearchResult(entry=entry, score=hit.get("distance", 0.0))
                )
        return search_results

    async def keyword_search(
        self,
        query: str,
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
        filter_expr = _build_filter_expr(
            run_id=run_id,
            task_id=task_id,
            source_type=source_type,
            min_confidence=min_confidence,
        )

        rows = self._client.query(
            collection_name=col_name,
            filter=filter_expr or "",
            limit=max(top_k * 20, 200),
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
                "embedding",
            ],
        )
        results = [
            SearchResult(
                entry=_entry_from_row(row),
                score=lexical_score(query, row.get("content", "")),
            )
            for row in rows
        ]
        results = [result for result in results if result.score > 0]
        results.sort(key=lambda result: result.score, reverse=True)
        return results[:top_k]

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
                entries.append(_entry_from_row(r))
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


def _entry_to_row(entry: MemoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "run_id": entry.run_id,
        "task_id": entry.task_id,
        "title": entry.title,
        "source_url": entry.source_url,
        "content": entry.content,
        "source_type": entry.source_type,
        "confidence": entry.confidence,
        "created_at": entry.created_at,
        "metadata_json": json.dumps(entry.metadata, ensure_ascii=False),
        "embedding": entry.embedding,
    }


def _entry_from_row(row: dict[str, Any], *, id_: str | None = None) -> MemoryEntry:
    return MemoryEntry(
        id=id_ if id_ is not None else row.get("id", ""),
        run_id=row.get("run_id", ""),
        task_id=row.get("task_id", ""),
        title=row.get("title", ""),
        source_url=row.get("source_url", ""),
        content=row.get("content", ""),
        source_type=row.get("source_type", ""),
        confidence=row.get("confidence", 0.0),
        created_at=row.get("created_at", ""),
        embedding=row.get("embedding", []),
        metadata=_loads_metadata(row.get("metadata_json", "")),
    )


def _build_filter_expr(
    *,
    run_id: str = "",
    task_id: str = "",
    source_type: str = "",
    min_confidence: float | None = None,
) -> str | None:
    filter_parts: list[str] = []
    if run_id:
        filter_parts.append(f'run_id == "{run_id}"')
    if task_id:
        filter_parts.append(f'task_id == "{task_id}"')
    if source_type:
        filter_parts.append(f'source_type == "{source_type}"')
    if min_confidence is not None:
        filter_parts.append(f"confidence >= {min_confidence}")
    return " and ".join(filter_parts) if filter_parts else None


def _embedding_dim_from_schema(schema: Any) -> int | None:
    fields = schema.get("fields", []) if isinstance(schema, dict) else []
    for schema_field in fields:
        if schema_field.get("name") != "embedding":
            continue
        params = schema_field.get("params") or schema_field.get("type_params") or {}
        dim = params.get("dim")
        return int(dim) if dim is not None else None
    return None
