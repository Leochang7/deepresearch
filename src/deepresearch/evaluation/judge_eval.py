from __future__ import annotations

import logging
from pathlib import Path

from deepresearch.core.json_repair import parse_json
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_eval.md"

JUDGE_DIMENSIONS = [
    "factuality",
    "citation_support",
    "completeness",
    "reasoning_consistency",
    "readability",
]

_DEFAULT_SCORES = {dim: 0.5 for dim in JUDGE_DIMENSIONS}


async def llm_as_judge(
    llm: LLMClient,
    question: str,
    report: ResearchReport,
    evidence: list[EvidenceItem],
) -> dict[str, float]:
    """Score a report on 5 dimensions using LLM."""
    system_prompt = (
        _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""
    )
    report_text = _format_report(report)
    evidence_text = "\n".join(
        f'[{e.evidence_id}] {e.claim}: "{e.quote}" ({e.citation})' for e in evidence
    )
    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(
            role="user",
            content=(
                f"Question: {question}\n\n"
                f"Report:\n{report_text}\n\n"
                f"Evidence:\n{evidence_text}\n\n"
                "Score the report on the 5 dimensions."
            ),
        ),
    ]
    response = await llm.chat(messages, json_mode=True)
    data = parse_json(response.content, strict=False)
    if not isinstance(data, dict):
        logger.warning("Judge returned non-dict, using default scores")
        return dict(_DEFAULT_SCORES)

    scores: dict[str, float] = {}
    for dim in JUDGE_DIMENSIONS:
        raw = data.get(dim)
        try:
            val = float(raw)
            scores[dim] = max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            scores[dim] = 0.5
    return scores


def _format_report(report: ResearchReport) -> str:
    parts = [f"# {report.question}"]
    if report.summary:
        parts.append(f"\n## Executive Summary\n{report.summary}")
    for section in report.sections:
        parts.append(f"\n## {section.title}\n{section.content}")
    if report.limitations:
        parts.append(
            "\n## Limitations\n" + "\n".join(f"- {item}" for item in report.limitations)
        )
    return "\n".join(parts)
