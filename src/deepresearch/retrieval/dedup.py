from __future__ import annotations

import hashlib

from deepresearch.schemas.evidence import RetrievedDocument


def dedup_documents(
    docs: list[RetrievedDocument],
) -> list[RetrievedDocument]:
    seen: set[str] = set()
    unique: list[RetrievedDocument] = []

    for doc in docs:
        key = _dedup_key(doc)
        if key not in seen:
            seen.add(key)
            unique.append(doc)

    return unique


def dedup_chunks(chunks: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []

    for chunk in chunks:
        h = hashlib.sha256(chunk.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(chunk)

    return unique


def _dedup_key(doc: RetrievedDocument) -> str:
    url = doc.url or ""
    content_hash = hashlib.sha256(doc.content.encode()).hexdigest()[:32]
    return f"{url}:{content_hash}"
