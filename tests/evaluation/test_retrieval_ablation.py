from __future__ import annotations

from pathlib import Path

import pytest

from deepresearch.config import DeepResearchConfig
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.evaluation.retrieval_ablation import run_retrieval_ablation


@pytest.mark.asyncio
async def test_retrieval_ablation_uses_real_dataset_and_corpus(tmp_path: Path):
    dataset = tmp_path / "bench.jsonl"
    dataset.write_text(
        '{"id":"case-1","domain":"rag","difficulty":"easy",'
        '"question":"How does BM25 improve hybrid RAG?",'
        '"expected_facts":[{"fact":"BM25 excels at exact keyword matching",'
        '"keywords":["BM25","keyword matching"]}],'
        '"required_citations":1,"tags":["rag"],'
        '"question_lang":"en","evidence_lang":"en"}\n',
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "rag.md").write_text(
        "# Hybrid RAG\n\nSparse retrieval like BM25 excels at exact keyword matching. "
        "Dense retrieval captures semantic similarity through embeddings.",
        encoding="utf-8",
    )
    (corpus / "other.md").write_text(
        "# Agents\n\nTool use lets agents call external functions.",
        encoding="utf-8",
    )

    report = await run_retrieval_ablation(
        dataset,
        corpus,
        MockEmbeddingClient(dim=16),
        top_k=5,
        cfg=DeepResearchConfig(),
    )

    assert report["evaluated_cases"] == 1
    assert report["top_k"] == 5
    assert report["recall"]["keyword_fact_recall_at_5"] == 1.0
    assert report["recall"]["rrf_hybrid_fact_recall_at_5"] == 1.0
    assert report["source_diversity"]["rrf_mmr_diversity_at_5"] >= 0.0
