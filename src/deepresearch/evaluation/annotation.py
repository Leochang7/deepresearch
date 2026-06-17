"""Annotation candidate selection for benchmark results.

Flag benchmark results that need human review based on configurable thresholds.
"""

from __future__ import annotations

import logging
from typing import Any

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
