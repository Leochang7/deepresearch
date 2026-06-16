from __future__ import annotations

from deepresearch.retrieval.query_expansion import expand_query


def test_expand_chinese_query_adds_english_terms():
    expanded = expand_query("什么是RAG检索增强生成")
    assert any("RAG" in q or "retrieval" in q.lower() for q in expanded)


def test_expand_english_query_no_change():
    expanded = expand_query("What is RAG?")
    assert expanded == ["What is RAG?"]


def test_expand_mixed_query():
    expanded = expand_query("LoRA低秩适配 fine-tuning")
    assert len(expanded) >= 2  # original + at least one expansion


def test_expand_empty_query():
    assert expand_query("") == [""]


def test_expand_preserves_original():
    expanded = expand_query("什么是大语言模型")
    assert expanded[0] == "什么是大语言模型"  # original always first


def test_expand_no_duplicate_expansions():
    expanded = expand_query("什么是RAG检索增强生成")
    assert len(expanded) == len(set(expanded))
