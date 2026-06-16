from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from deepresearch.evaluation.benchmark import compare_summaries


def run_suite_summary(
    output_dir: Path,
    *,
    expected_datasets: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate summaries from multiple experiment subdirectories."""
    suite: dict[str, Any] = {
        "output_dir": str(output_dir),
        "datasets": {},
        "missing_datasets": [],
        "failed_datasets": [],
    }
    for summary_path in sorted(output_dir.glob("*/summary.json")):
        name = summary_path.parent.name
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_stats = _result_error_stats(summary_path.parent / "results.jsonl")
        summary["result_error_count"] = result_stats["error_count"]
        summary["result_count"] = result_stats["result_count"]
        suite["datasets"][name] = summary
        if result_stats["error_count"]:
            suite["failed_datasets"].append(name)
    if expected_datasets:
        suite["missing_datasets"] = [
            name for name in expected_datasets if name not in suite["datasets"]
        ]
        suite["failed_datasets"].extend(
            name
            for name in suite["missing_datasets"]
            if name not in suite["failed_datasets"]
        )
    suite["dataset_count"] = len(suite["datasets"])
    return suite


def generate_comparison(
    before_dir: Path,
    after_dir: Path,
) -> dict[str, Any]:
    """Compare two experiment output directories."""
    comparison: dict[str, Any] = {}
    for summary_file in sorted(after_dir.glob("*/summary.json")):
        name = summary_file.parent.name
        before_summary = before_dir / name / "summary.json"
        if before_summary.exists():
            before = json.loads(before_summary.read_text(encoding="utf-8"))
            after = json.loads(summary_file.read_text(encoding="utf-8"))
            comparison[name] = compare_summaries(before, after)
    return comparison


def write_suite_artifacts(
    output_dir: Path,
    *,
    expected_datasets: list[str] | None = None,
    before_dir: Path | None = None,
) -> dict[str, Any]:
    """Write suite_summary.json and comparison.json into an experiment suite dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    suite = run_suite_summary(output_dir, expected_datasets=expected_datasets)
    comparison = generate_comparison(before_dir, output_dir) if before_dir else {}

    (output_dir / "suite_summary.json").write_text(
        json.dumps(suite, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "comparison.json").write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"suite_summary": suite, "comparison": comparison}


def _result_error_stats(results_path: Path) -> dict[str, int]:
    if not results_path.exists():
        return {"result_count": 0, "error_count": 0}
    result_count = 0
    error_count = 0
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        result_count += 1
        data = json.loads(line)
        if data.get("evaluation", {}).get("error"):
            error_count += 1
    return {"result_count": result_count, "error_count": error_count}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark comparison utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    suite_parser = subparsers.add_parser("suite", help="Write suite artifacts")
    suite_parser.add_argument("output_dir")
    suite_parser.add_argument("--expected", default="")
    suite_parser.add_argument("--before", default="")

    args = parser.parse_args(argv)
    if args.command == "suite":
        expected = [item for item in args.expected.split(",") if item]
        before = Path(args.before) if args.before else None
        write_suite_artifacts(
            Path(args.output_dir),
            expected_datasets=expected or None,
            before_dir=before,
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
