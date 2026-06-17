from __future__ import annotations

import json

from deepresearch.evaluation.quantification import (
    generate_quantification_report,
    json_repair_report,
    mmr_preservation_report,
    retrieval_ablation_report,
    write_quantification_report,
)


def test_json_repair_report_shows_fallback_gain():
    report = json_repair_report()

    assert report["strict_success_rate"] < report["fallback_success_rate"]
    assert report["fallback_success_rate"] >= 0.9


def test_retrieval_ablation_report_shows_rrf_gain():
    report = retrieval_ablation_report()

    assert report["pure_vector_recall_at_5"] < report["rrf_hybrid_recall_at_5"]
    assert report["rrf_hybrid_recall_at_5"] == 1.0


def test_mmr_preservation_report_increases_source_diversity():
    report = mmr_preservation_report()

    assert report["mmr_unique_source_count"] > report["naive_unique_source_count"]
    assert report["mmr_unique_source_ratio"] > report["naive_unique_source_ratio"]


def test_write_quantification_report(tmp_path):
    output = tmp_path / "summary.json"

    report = write_quantification_report(output)

    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_generate_quantification_report_contains_resume_claim_inputs():
    report = generate_quantification_report()

    assert set(report) >= {
        "json_repair",
        "retrieval_ablation",
        "mmr_preservation",
    }
