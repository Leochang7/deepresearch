from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

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


@dataclass(frozen=True)
class LexicalPolicy:
    tokenizer: str = "builtin"
    latin_min_chars: int = 2
    cjk_ngrams: tuple[int, ...] = (1, 2)
    cjk_ngram_fallback: bool = True
    userdict_path: str = ""
    stopwords: set[str] = field(default_factory=lambda: set(DEFAULT_STOPWORDS))

    def tokenize(self, text: str) -> set[str]:
        normalized = text.lower()
        latin = {
            token
            for token in re.findall(r"[a-z][a-z0-9_-]*", normalized)
            if len(token) >= self.latin_min_chars
        }
        latin -= self.stopwords

        if self.tokenizer == "jieba":
            return latin | self._jieba_tokens(normalized)
        return latin | _cjk_ngram_tokens(normalized, self.cjk_ngrams)

    def score(self, query: str, content: str) -> float:
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return 0.0
        content_tokens = self.tokenize(content)
        return len(query_tokens & content_tokens) / len(query_tokens)

    def _jieba_tokens(self, text: str) -> set[str]:
        import jieba

        _load_jieba_userdict(self.userdict_path)
        tokens = {
            token.strip().lower()
            for token in jieba.lcut(text, cut_all=False)
            if token.strip() and not token.isspace()
        }
        if self.cjk_ngram_fallback:
            tokens |= _cjk_ngram_tokens(text, self.cjk_ngrams)
        return tokens


_DEFAULT_POLICY = LexicalPolicy()
_JIEBA_USERDICTS_LOADED: set[str] = set()


def configure_lexical_policy(policy: LexicalPolicy) -> None:
    global _DEFAULT_POLICY
    _DEFAULT_POLICY = policy


def get_lexical_policy() -> LexicalPolicy:
    return _DEFAULT_POLICY


def lexical_tokens(text: str) -> set[str]:
    return _DEFAULT_POLICY.tokenize(text)


def lexical_score(query: str, content: str) -> float:
    return _DEFAULT_POLICY.score(query, content)


def _cjk_ngram_tokens(text: str, ngrams: tuple[int, ...]) -> set[str]:
    cjk_runs = re.findall(r"[\u3400-\u9fff]+", text)
    tokens: set[str] = set()
    for run in cjk_runs:
        for ngram in ngrams:
            if ngram <= 0 or len(run) < ngram:
                continue
            tokens.update(
                run[index : index + ngram] for index in range(len(run) - ngram + 1)
            )
    return tokens


def _load_jieba_userdict(userdict_path: str) -> None:
    path = userdict_path or _default_userdict_path()
    if not path or path in _JIEBA_USERDICTS_LOADED:
        return

    import jieba

    userdict = Path(path)
    if userdict.is_file():
        jieba.load_userdict(str(userdict))
        _JIEBA_USERDICTS_LOADED.add(path)


def _default_userdict_path() -> str:
    try:
        path = resources.files("deepresearch.retrieval").joinpath("jieba_userdict.txt")
    except (FileNotFoundError, ModuleNotFoundError):
        return ""
    return str(path) if path.is_file() else ""
