from __future__ import annotations

import re

DEFAULT_STOPWORDS = {
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


def lexical_tokens(
    text: str,
    *,
    latin_min_chars: int = 2,
    stopwords: set[str] | None = DEFAULT_STOPWORDS,
) -> set[str]:
    normalized = text.lower()
    latin = {
        token
        for token in re.findall(r"[a-z][a-z0-9_-]*", normalized)
        if len(token) >= latin_min_chars
    }
    if stopwords:
        latin -= stopwords

    cjk_runs = re.findall(r"[\u3400-\u9fff]+", normalized)
    cjk: set[str] = set()
    for run in cjk_runs:
        cjk.update(run)
        cjk.update(run[index : index + 2] for index in range(len(run) - 1))
    return latin | cjk


def lexical_score(query: str, content: str) -> float:
    query_tokens = lexical_tokens(query)
    if not query_tokens:
        return 0.0
    content_tokens = lexical_tokens(content)
    return len(query_tokens & content_tokens) / len(query_tokens)
