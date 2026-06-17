from __future__ import annotations

import logging

from deepresearch.agents.prompting import load_agent_prompt
from deepresearch.agents.report_formatting import format_report_for_review
from deepresearch.core.json_repair import parse_json
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.prompts.provider import PromptProvider
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport

logger = logging.getLogger(__name__)

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
    prompt_provider: PromptProvider | None = None,
) -> dict[str, float]:
    """Score a report on 5 dimensions using LLM."""
    system_prompt = load_agent_prompt(prompt_provider, "judge_eval")
    report_text = format_report_for_review(report)
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
    try:
        response = await llm.chat(messages, json_mode=True)
    except Exception as exc:
        logger.warning("Judge LLM call failed: %s", exc, exc_info=True)
        result = dict(_DEFAULT_SCORES)
        result["__failure_reason"] = f"LLM call failed: {exc}"
        return result
    data = parse_json(response.content, strict=False)
    if not isinstance(data, dict):
        logger.warning("Judge returned non-dict, using default scores")
        result = dict(_DEFAULT_SCORES)
        result["__failure_reason"] = "Judge returned non-dict response"
        return result

    scores: dict[str, float] = {}
    for dim in JUDGE_DIMENSIONS:
        raw = data.get(dim)
        try:
            val = float(raw)
            scores[dim] = max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            scores[dim] = 0.5
    return scores


async def judge_facts(
    llm: LLMClient,
    question: str,
    report: ResearchReport,
    evidence: list[EvidenceItem],
    fact_details: list[dict],
    prompt_provider: PromptProvider | None = None,
) -> list[dict]:
    """Evaluate unmatched facts using LLM semantic judge.

    Only facts with matched=False are sent to the LLM.
    Returns updated fact_details with judge verdicts merged in.
    """
    system_prompt = load_agent_prompt(prompt_provider, "fact_judge")
    report_text = format_report_for_review(report)
    evidence_text = "\n".join(
        f'[{e.evidence_id}] {e.claim}: "{e.quote}" ({e.citation})' for e in evidence
    )
    valid_evidence_ids = {e.evidence_id for e in evidence}

    updated: list[dict] = []
    for detail in fact_details:
        if detail.get("matched"):
            updated.append(detail)
            continue

        fact = detail.get("fact", "")
        try:
            messages = [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(
                    role="user",
                    content=(
                        f"Question: {question}\n\n"
                        f"Report:\n{report_text}\n\n"
                        f"Evidence:\n{evidence_text}\n\n"
                        f"Fact to verify: {fact}\n\n"
                        "Does the report support this fact?"
                    ),
                ),
            ]
            response = await llm.chat(messages, json_mode=True)
            data = parse_json(response.content, strict=False)
            if not isinstance(data, dict):
                logger.warning(
                    "Fact judge returned non-dict for '%s', using rule result",
                    fact[:50],
                )
                updated.append(detail)
                continue

            verdict = data.get("verdict")
            if verdict not in {"hit", "miss", "uncertain"}:
                logger.warning(
                    "Fact judge returned invalid verdict for '%s', using rule result",
                    fact[:50],
                )
                updated.append(detail)
                continue
            supporting_ids = data.get("supporting_evidence_ids", [])
            reason = data.get("reason", "")
            valid_supporting_ids = (
                [
                    str(eid)
                    for eid in supporting_ids
                    if isinstance(eid, str) and eid in valid_evidence_ids
                ]
                if isinstance(supporting_ids, list)
                else []
            )

            merged = dict(detail)
            merged["source"] = "judge"
            merged["matched"] = verdict == "hit"
            merged["reason"] = f"[judge:{verdict}] {reason}"
            merged["supporting_evidence_ids"] = valid_supporting_ids
            updated.append(merged)

        except Exception:
            logger.warning(
                "Fact judge failed for '%s', falling back to rule result",
                fact[:50],
                exc_info=True,
            )
            updated.append(dict(detail))

    return updated
