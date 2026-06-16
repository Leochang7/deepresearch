from __future__ import annotations

import re

# Common Chinese-English term mappings for AI/ML domain
_TERM_ALIASES: dict[str, list[str]] = {
    "检索增强生成": ["RAG", "retrieval-augmented generation"],
    "低秩适配": ["LoRA", "low-rank adaptation"],
    "向量检索": ["vector retrieval", "dense retrieval"],
    "稀疏检索": ["sparse retrieval", "BM25"],
    "密集检索": ["dense retrieval", "embedding search"],
    "微调": ["fine-tuning"],
    "大语言模型": ["LLM", "large language model"],
    "提示工程": ["prompt engineering"],
    "思维链": ["chain-of-thought", "CoT"],
    "自一致性": ["self-consistency"],
    "注意力机制": ["attention mechanism"],
    "变换器": ["transformer"],
    "嵌入": ["embedding"],
    "重排序": ["reranking"],
    "知识图谱": ["knowledge graph"],
    "多智能体": ["multi-agent"],
    "工具使用": ["tool use", "function calling"],
    "参数高效": ["parameter-efficient", "PEFT"],
}


def expand_query(query: str) -> list[str]:
    """Expand a Chinese query with English term aliases.

    Returns a list of queries: the original plus English expansions.
    English-only queries pass through unchanged.
    """
    if not query or not re.search(r"[㐀-鿿]", query):
        return [query]

    expansions = [query]
    for zh_term, en_terms in _TERM_ALIASES.items():
        if zh_term in query:
            for en_term in en_terms:
                expanded = query.replace(zh_term, en_term)
                if expanded not in expansions:
                    expansions.append(expanded)

    return expansions
