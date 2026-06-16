import json

import pytest

from deepresearch.evaluation.compare import generate_comparison, run_suite_summary


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
            json.dumps({"avg_task_success_rate": 0.7}), encoding="utf-8",
        )
    result = run_suite_summary(tmp_path)
    assert result["dataset_count"] == 2
    assert "exp-a" in result["datasets"]
