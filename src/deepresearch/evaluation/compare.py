from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deepresearch.evaluation.benchmark import compare_summaries


def run_suite_summary(output_dir: Path) -> dict[str, Any]:
    """Aggregate summaries from multiple experiment subdirectories."""
    suite: dict[str, Any] = {"datasets": {}}
    for summary_path in sorted(output_dir.glob("*/summary.json")):
        name = summary_path.parent.name
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        suite["datasets"][name] = summary
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
