from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from deepresearch.retrieval.base import Retriever
from deepresearch.schemas.evidence import RetrievedDocument

_STOPWORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "been",
    "being",
    "can",
    "does",
    "from",
    "have",
    "how",
    "into",
    "main",
    "models",
    "that",
    "the",
    "their",
    "these",
    "this",
    "through",
    "what",
    "when",
    "where",
    "which",
    "with",
}


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

        query_tokens = _tokenize(" ".join(queries))
        scored: list[tuple[int, RetrievedDocument]] = []
        for doc in docs:
            score = _score_document(query_tokens, doc)
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        if any(score > 0 for score, _ in scored):
            scored = [(score, doc) for score, doc in scored if score > 0]
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


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in _STOPWORDS
    }


def _score_document(query_tokens: set[str], doc: RetrievedDocument) -> int:
    if not query_tokens:
        return 0
    content_tokens = _tokenize(doc.content)
    title_tokens = _tokenize(doc.title)
    url_tokens = _tokenize(doc.url or "")
    content_hits = len(query_tokens & content_tokens)
    title_hits = len(query_tokens & title_tokens)
    url_hits = len(query_tokens & url_tokens)
    return content_hits + (title_hits * 3) + url_hits
