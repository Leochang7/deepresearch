from __future__ import annotations

import hashlib
import json
from pathlib import Path

from deepresearch.retrieval.base import Retriever
from deepresearch.schemas.evidence import RetrievedDocument


class LocalDatasetRetriever(Retriever):
    def __init__(self, corpus_dir: str | Path) -> None:
        self._corpus_dir = Path(corpus_dir)

    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str = "",
        task_id: str = "",
        top_k: int = 10,
    ) -> list[RetrievedDocument]:
        if not self._corpus_dir.is_dir():
            return []

        docs: list[RetrievedDocument] = []
        for f in self._corpus_dir.iterdir():
            if f.suffix not in (".md", ".jsonl", ".txt"):
                continue
            if f.suffix == ".jsonl":
                docs.extend(_load_jsonl(f))
            else:
                docs.append(_load_text_file(f))

        query_lower = " ".join(queries).lower()
        scored = []
        for doc in docs:
            overlap = sum(1 for w in query_lower.split() if w in doc.content.lower())
            scored.append((overlap, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]


def _load_text_file(path: Path) -> RetrievedDocument:
    content = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return RetrievedDocument(
        id=f"local-{content_hash}",
        title=path.stem,
        content=content,
        source_type="local_dataset",
        url=str(path),
    )


def _load_jsonl(path: Path) -> list[RetrievedDocument]:
    docs: list[RetrievedDocument] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        content = item.get("content", "")
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        docs.append(
            RetrievedDocument(
                id=item.get("id") or f"local-{content_hash}",
                title=item.get("title") or f"{path.stem}:{line_no}",
                url=item.get("url") or str(path),
                source_type=item.get("source_type") or "local_dataset",
                content=content,
                published_at=item.get("published_at"),
                retrieved_at=item.get("retrieved_at", ""),
                metadata=item.get("metadata", {}),
            )
        )
    return docs
