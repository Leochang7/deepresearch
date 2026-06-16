import json

import pytest

from deepresearch.evaluation.compare import (
    generate_comparison,
    run_suite_summary,
    write_suite_artifacts,
)


def test_generate_comparison(tmp_path):
    before = tmp_path / "before" / "exp1"
    before.mkdir(parents=True)
    (before / "summary.json").write_text(
        json.dumps({"avg_task_success_rate": 0.6, "avg_citation_coverage": 0.5}),
        encoding="utf-8",
    )
    after = tmp_path / "after" / "exp1"
    after.mkdir(parents=True)
    (after / "summary.json").write_text(
        json.dumps({"avg_task_success_rate": 0.8, "avg_citation_coverage": 0.7}),
        encoding="utf-8",
    )
    result = generate_comparison(tmp_path / "before", tmp_path / "after")
    assert "exp1" in result
    assert result["exp1"]["avg_task_success_rate"]["delta"] == pytest.approx(0.2)


def test_run_suite_summary(tmp_path):
    for name in ("exp-a", "exp-b"):
        d = tmp_path / name
        d.mkdir()
        (d / "summary.json").write_text(
            json.dumps({"avg_task_success_rate": 0.7}),
            encoding="utf-8",
        )
    result = run_suite_summary(tmp_path)
    assert result["dataset_count"] == 2
    assert "exp-a" in result["datasets"]


def test_run_suite_summary_records_missing_and_failed_datasets(tmp_path):
    d = tmp_path / "exp-a"
    d.mkdir()
    (d / "summary.json").write_text(
        json.dumps({"avg_task_success_rate": 0.7}), encoding="utf-8"
    )
    (d / "results.jsonl").write_text(
        json.dumps({"evaluation": {"error": "failed"}}) + "\n",
        encoding="utf-8",
    )

    result = run_suite_summary(tmp_path, expected_datasets=["exp-a", "exp-b"])

    assert result["missing_datasets"] == ["exp-b"]
    assert result["failed_datasets"] == ["exp-a", "exp-b"]
    assert result["datasets"]["exp-a"]["result_error_count"] == 1


def test_write_suite_artifacts(tmp_path):
    d = tmp_path / "exp-a"
    d.mkdir()
    (d / "summary.json").write_text(
        json.dumps({"avg_task_success_rate": 0.7}), encoding="utf-8"
    )

    result = write_suite_artifacts(tmp_path, expected_datasets=["exp-a"])

    assert (tmp_path / "suite_summary.json").exists()
    assert (tmp_path / "comparison.json").exists()
    assert result["suite_summary"]["dataset_count"] == 1
