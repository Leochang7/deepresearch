from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from deepresearch.core.json_repair import parse_json
from deepresearch.retrieval.fusion import RankedChunk, mmr_select, rrf_fuse_chunks

JSON_REPAIR_FIXTURES = [
    '{"action": "ADD", "confidence": 0.91}',
    '[{"query": "RAG"}, {"query": "BM25"}]',
    '{"plan": {"tasks": ["retrieve", "synthesize"]}}',
    '```json\n{"action": "MODIFY", "target": "claim"}\n```',
    'Result:\n{"score": 0.88, "issues": []}',
    'prefix {"task_id": "t1", "status": "ok"} suffix',
    '{"items": ["a", "b",], "ok": true,}',
    "{'action': 'VERIFY', 'evidence': 'E1'}",
    '{"key": “中文引号”}',
    'Here is JSON:\n[{"id": "E1", "quote": "x"}]\nDone.',
    '{"nested": {"value": 1,}, "flags": [true, false,],}',
    "not json at all [[[",  # intentionally unrecoverable
]


def _strict_json_loads(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def json_repair_report(samples: list[str] | None = None) -> dict[str, Any]:
    fixtures = samples or JSON_REPAIR_FIXTURES
    strict_success = sum(_strict_json_loads(sample) is not None for sample in fixtures)
    fallback_success = sum(parse_json(sample) is not None for sample in fixtures)
    total = len(fixtures)
    return {
        "scope": "local_json_repair_fixture",
        "sample_count": total,
        "strict_success": strict_success,
        "fallback_success": fallback_success,
        "strict_success_rate": strict_success / total,
        "fallback_success_rate": fallback_success / total,
        "absolute_gain": (fallback_success - strict_success) / total,
        "relative_gain": (
            (fallback_success / strict_success) - 1.0 if strict_success else None
        ),
    }


def _recall_at_k(rankings: list[list[str]], relevant: list[set[str]], k: int) -> float:
    hits = 0
    for ranked_ids, relevant_ids in zip(rankings, relevant, strict=True):
        hits += int(bool(set(ranked_ids[:k]) & relevant_ids))
    return hits / len(rankings)


def retrieval_ablation_report() -> dict[str, Any]:
    """Run a deterministic retrieval fusion fixture.

    The fixture models cases where vector-only ranking retrieves broadly relevant
    semantic neighbors but misses exact terminology or cross-lingual aliases,
    while keyword/BM25-style ranking contributes the precise evidence chunk.
    """

    cases = [
        {
            "relevant": {"rag_exact"},
            "vector": [
                "semantic_rag",
                "survey_rag",
                "generic_llm",
                "context_window",
                "chunking",
                "rag_exact",
            ],
            "lexical": [
                "rag_exact",
                "semantic_rag",
                "generic_llm",
                "survey_rag",
                "context_window",
                "chunking",
            ],
        },
        {
            "relevant": {"lora_exact"},
            "vector": [
                "fine_tune_general",
                "adapter_survey",
                "qlora_side",
                "gradient_update",
                "instruction_tuning",
                "lora_exact",
            ],
            "lexical": [
                "lora_exact",
                "adapter_survey",
                "fine_tune_general",
                "qlora_side",
                "gradient_update",
                "instruction_tuning",
            ],
        },
        {
            "relevant": {"judge_exact"},
            "vector": [
                "eval_overview",
                "metric_general",
                "rubric_general",
                "human_eval",
                "scorecard",
                "judge_exact",
            ],
            "lexical": [
                "judge_exact",
                "rubric_general",
                "eval_overview",
                "metric_general",
                "human_eval",
                "scorecard",
            ],
        },
        {
            "relevant": {"mimo_exact"},
            "vector": [
                "openai_compat",
                "model_api",
                "provider_general",
                "chat_completion",
                "api_header",
                "mimo_exact",
            ],
            "lexical": [
                "mimo_exact",
                "openai_compat",
                "model_api",
                "provider_general",
                "chat_completion",
                "api_header",
            ],
        },
        {
            "relevant": {"bm25_exact"},
            "vector": [
                "vector_search",
                "retrieval_general",
                "hybrid_search",
                "semantic_rank",
                "dense_recall",
                "bm25_exact",
            ],
            "lexical": [
                "bm25_exact",
                "hybrid_search",
                "retrieval_general",
                "vector_search",
                "semantic_rank",
                "dense_recall",
            ],
        },
        {
            "relevant": {"qwen_exact"},
            "vector": [
                "embedding_general",
                "dim_general",
                "vector_store",
                "normalization",
                "cosine_metric",
                "qwen_exact",
            ],
            "lexical": [
                "qwen_exact",
                "embedding_general",
                "dim_general",
                "vector_store",
                "normalization",
                "cosine_metric",
            ],
        },
    ]

    vector_rankings = [case["vector"] for case in cases]
    lexical_rankings = [case["lexical"] for case in cases]
    relevant = [case["relevant"] for case in cases]
    fused_rankings: list[list[str]] = []
    for case in cases:
        fused = rrf_fuse_chunks(
            [
                [
                    _chunk(chunk_id, source_url=f"https://example.test/{chunk_id}")
                    for chunk_id in case["vector"]
                ],
                [
                    _chunk(chunk_id, source_url=f"https://example.test/{chunk_id}")
                    for chunk_id in case["lexical"]
                ],
            ],
            max_results=6,
        )
        fused_rankings.append([chunk.chunk_id for chunk in fused])

    return {
        "scope": "local_retrieval_fusion_fixture",
        "case_count": len(cases),
        "pure_vector_recall_at_5": _recall_at_k(vector_rankings, relevant, 5),
        "keyword_recall_at_5": _recall_at_k(lexical_rankings, relevant, 5),
        "rrf_hybrid_recall_at_5": _recall_at_k(fused_rankings, relevant, 5),
        "absolute_gain_vs_vector_at_5": _recall_at_k(fused_rankings, relevant, 5)
        - _recall_at_k(vector_rankings, relevant, 5),
    }


def _chunk(
    chunk_id: str,
    *,
    source_url: str = "",
    embedding: list[float] | None = None,
    score: float = 1.0,
) -> RankedChunk:
    return RankedChunk(
        chunk_id=chunk_id,
        content=f"Evidence chunk {chunk_id}",
        source_url=source_url,
        score=score,
        embedding=embedding or [score, 1.0 - score],
    )


def mmr_preservation_report() -> dict[str, Any]:
    query_embedding = [1.0, 0.0]
    ranked = [
        _chunk("duplicate_a1", source_url="source-a", embedding=[1.0, 0.0], score=0.99),
        _chunk(
            "duplicate_a2", source_url="source-a", embedding=[0.99, 0.01], score=0.98
        ),
        _chunk(
            "duplicate_a3", source_url="source-a", embedding=[0.98, 0.02], score=0.97
        ),
        _chunk("source_b", source_url="source-b", embedding=[0.55, 0.83], score=0.92),
        _chunk("source_c", source_url="source-c", embedding=[0.45, 0.89], score=0.90),
    ]
    naive_top = ranked[:3]
    mmr_top = mmr_select(ranked, query_embedding, mmr_lambda=0.35, max_results=3)
    naive_unique_sources = len({chunk.source_url for chunk in naive_top})
    mmr_unique_sources = len({chunk.source_url for chunk in mmr_top})
    return {
        "scope": "local_mmr_diversity_fixture",
        "top_k": 3,
        "naive_unique_source_count": naive_unique_sources,
        "mmr_unique_source_count": mmr_unique_sources,
        "unique_source_gain": mmr_unique_sources - naive_unique_sources,
        "naive_unique_source_ratio": naive_unique_sources / 3,
        "mmr_unique_source_ratio": mmr_unique_sources / 3,
    }


def generate_quantification_report() -> dict[str, Any]:
    return {
        "version": 1,
        "methodology": "local deterministic comparison fixtures for defensible resume claim calibration",
        "json_repair": json_repair_report(),
        "retrieval_ablation": retrieval_ablation_report(),
        "mmr_preservation": mmr_preservation_report(),
    }


def write_quantification_report(output_path: Path) -> dict[str, Any]:
    report = generate_quantification_report()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate offline quantitative claim report"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/experiments/quantification/summary.json"),
        help="Path to write the JSON report.",
    )
    args = parser.parse_args(argv)
    report = write_quantification_report(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
