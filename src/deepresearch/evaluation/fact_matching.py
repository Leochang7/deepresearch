from __future__ import annotations

import re
from typing import Any

from deepresearch.retrieval.lexical import lexical_tokens
from deepresearch.schemas.evaluation import ExpectedFact, FactHitResult

FactSpec = str | dict[str, Any] | ExpectedFact

_ABBREVIATIONS: dict[str, list[str]] = {
    "llm": ["large language model", "large language models", "大语言模型"],
    "large language model": ["llm"],
    "large language models": ["llm"],
    "大语言模型": ["llm"],
    "rag": [
        "retrieval-augmented generation",
        "retrieval augmented generation",
        "检索增强生成",
    ],
    "retrieval-augmented generation": ["rag"],
    "检索增强生成": ["rag"],
    "cot": ["chain-of-thought", "chain of thought", "思维链"],
    "chain-of-thought": ["cot"],
    "思维链": ["cot"],
    "rlhf": [
        "reinforcement learning from human feedback",
        "reinforcement learning with human feedback",
    ],
    "reinforcement learning from human feedback": ["rlhf"],
    "lora": ["low-rank adaptation", "low rank adaptation", "低秩适配"],
    "low-rank adaptation": ["lora"],
    "低秩适配": ["lora"],
    "bert": ["bidirectional encoder representations from transformers"],
    "tf-idf": ["term frequency inverse document frequency"],
    "kv-cache": ["key value cache", "kv cache"],
    "bm25": ["best matching 25"],
    "gpt": ["generative pre-trained transformer", "generative pretrained transformer"],
    "vae": ["variational autoencoder", "variational auto-encoder"],
    "gan": ["generative adversarial network"],
    "self-attention": ["自注意力"],
    "自注意力": ["self-attention"],
}


def _normalize_text(text: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", text)
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def _detect_language(text: str) -> str:
    if re.search(r"[㐀-鿿]", text):
        return "zh"
    return "en"


def _tokenize_for_match(text: str) -> set[str]:
    return lexical_tokens(text)


def _expand_abbreviations(tokens: list[str]) -> set[str]:
    expanded: set[str] = set(tokens)
    for token in tokens:
        if token in _ABBREVIATIONS:
            for expansion in _ABBREVIATIONS[token]:
                for t in expansion.split():
                    expanded.add(t)
    for key, expansions in _ABBREVIATIONS.items():
        for expansion in expansions:
            expansion_tokens = set(expansion.split())
            if expansion_tokens & set(tokens):
                expanded.add(key)
                for t in key.split():
                    expanded.add(t)
    return expanded


def _parse_fact_spec(spec: FactSpec) -> tuple[str, list[str]]:
    if isinstance(spec, str):
        return spec, []
    if isinstance(spec, ExpectedFact):
        return spec.fact, [*spec.keywords, *spec.aliases]
    fact_text = spec.get("fact", "")
    extra_keywords: list[str] = []
    extra_keywords.extend(spec.get("keywords", []))
    extra_keywords.extend(spec.get("aliases", []))
    return fact_text, extra_keywords


def _evaluate_fact(spec: FactSpec, text_lower: str) -> FactHitResult:
    fact_text, extra_keywords = _parse_fact_spec(spec)
    if not fact_text.strip():
        return FactHitResult(fact=fact_text, matched=False, reason="Empty fact text")

    norm_text = _normalize_text(text_lower)
    norm_fact = _normalize_text(fact_text)

    tokens = sorted(_tokenize_for_match(norm_fact) - {""})
    tokens = [t for t in tokens if len(t) > 1 or re.match(r"[㐀-鿿]", t)]
    if not tokens:
        return FactHitResult(
            fact=fact_text, matched=False, reason="No meaningful tokens"
        )

    if norm_fact in norm_text:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=tokens,
            unmatched_keywords=[],
            reason="Full phrase match",
        )

    latin_tokens = [t for t in tokens if re.match(r"[a-z]", t)]
    cjk_extra: list[str] = []
    latin_extra: list[str] = []
    for kw in extra_keywords:
        norm_kw = _normalize_text(kw)
        if re.search(r"[㐀-鿿]", norm_kw):
            cjk_extra.append(norm_kw)
        else:
            latin_extra.append(norm_kw)
    expanded = _expand_abbreviations(latin_tokens + latin_extra)

    matched: list[str] = []
    unmatched: list[str] = []
    for t in tokens:
        if t in norm_text:
            matched.append(t)
        else:
            unmatched.append(t)

    cjk_extra_matched: list[str] = []
    for kw in cjk_extra:
        if kw in norm_text:
            cjk_extra_matched.append(kw)

    expanded_matched: list[str] = []
    expanded_unmatched: list[str] = []
    for t in expanded:
        if t in norm_text:
            expanded_matched.append(t)
        else:
            expanded_unmatched.append(t)

    if len(tokens) > 0 and len(matched) / len(tokens) >= 0.5:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=matched,
            unmatched_keywords=unmatched,
            reason=f"Token overlap {len(matched)}/{len(tokens)} >= 50%",
        )

    if cjk_extra and cjk_extra_matched:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=matched + cjk_extra_matched,
            unmatched_keywords=unmatched,
            reason=f"CJK keyword match {len(cjk_extra_matched)}/{len(cjk_extra)}",
        )

    if len(expanded) > 0 and len(expanded_matched) / len(expanded) >= 0.5:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=expanded_matched,
            unmatched_keywords=expanded_unmatched,
            reason=f"Expanded keyword overlap {len(expanded_matched)}/{len(expanded)} >= 50%",
        )

    reason = (
        f"Token overlap {len(matched)}/{len(tokens)} < 50%; "
        f"expanded overlap {len(expanded_matched)}/{len(expanded)} < 50%"
    )
    fact_lang = _detect_language(fact_text)
    text_lang = _detect_language(text_lower)
    if fact_lang != text_lang:
        reason += f"; language mismatch: fact is {fact_lang}, report is {text_lang}"

    return FactHitResult(
        fact=fact_text,
        matched=False,
        matched_keywords=matched,
        unmatched_keywords=unmatched,
        reason=reason,
    )


def _fact_in_text(fact: str, text_lower: str) -> bool:
    return _evaluate_fact(fact, text_lower).matched
