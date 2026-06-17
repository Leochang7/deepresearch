"""Annotation candidate selection for benchmark results.

Flag benchmark results that need human review based on configurable thresholds.
"""

from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from deepresearch.evaluation.langfuse import LangfuseAdapter

logger = logging.getLogger(__name__)


def select_annotation_candidates(
    results: list[dict[str, Any]],
    *,
    min_citation_coverage: float = 0.3,
    min_factual_hit_rate: float = 0.5,
    flag_hallucination: bool = True,
    min_judge_divergence: float = 0.3,
) -> list[dict[str, Any]]:
    """Select benchmark results that need human review.

    A result is selected if ANY of these conditions hold:
    - citation_coverage < min_citation_coverage
    - factual_hit_rate < min_factual_hit_rate
    - hallucination_flag is True (when flag_hallucination)
    - judge score divergence > min_judge_divergence (max - min across dimensions)

    Missing fields default to 0 / False, making them more likely to be flagged.
    """
    candidates: list[dict[str, Any]] = []
    for r in results:
        evaluation = r.get("evaluation", {})
        reasons: list[str] = []

        cc = evaluation.get("citation_coverage", 0)
        if cc < min_citation_coverage:
            reasons.append(f"low_citation_coverage={cc}")

        fhr = evaluation.get("factual_hit_rate", 0)
        if fhr < min_factual_hit_rate:
            reasons.append(f"low_factual_hit_rate={fhr}")

        if flag_hallucination and evaluation.get("hallucination_flag", False):
            reasons.append("hallucination_flag=True")

        judge_scores = evaluation.get("judge_scores", {})
        if judge_scores and len(judge_scores) >= 2:
            vals = [v for v in judge_scores.values() if isinstance(v, (int, float))]
            if vals:
                divergence = max(vals) - min(vals)
                if divergence > min_judge_divergence:
                    reasons.append(f"judge_divergence={divergence:.2f}")

        if reasons:
            candidates.append({**r, "annotation_reasons": reasons})

    return candidates


def push_annotations(
    adapter: LangfuseAdapter,
    candidates: list[dict[str, Any]],
    *,
    queue_name: str = "deepresearch_review",
) -> int:
    """Push annotation candidates to Langfuse. Returns count pushed."""
    return adapter.push_annotations(queue_name=queue_name, items=candidates)


def import_annotations(
    annotations_path: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Merge human annotations into a benchmark summary.

    Reads a JSONL file where each line has {"case_id": ..., "verdict": ..., ...}.
    Adds a "human_annotations" dict keyed by case_id to the summary.
    Never overwrites existing summary fields.
    """
    if not annotations_path.is_file():
        return summary

    annotations: dict[str, dict[str, Any]] = {}
    for line in annotations_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        with contextlib.suppress(Exception):
            entry = json.loads(line)
            case_id = entry.get("case_id", "")
            if case_id:
                annotations[case_id] = entry

    if annotations:
        result = dict(summary)
        result["human_annotations"] = annotations
        return result
    return summary
