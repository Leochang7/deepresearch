import json

import pytest

from deepresearch.evaluation.judge_eval import JUDGE_DIMENSIONS, llm_as_judge
from deepresearch.llm.mock import MockLLM
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport


def _report() -> ResearchReport:
    return ResearchReport(
        run_id="r1",
        question="test question",
        summary="Test summary [E1].",
        sections=[ReportSection(title="Analysis", content="Analysis [E1].")],
    )


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            evidence_id="E1",
            task_id="t1",
            claim="Test claim",
            quote="Test quote",
            citation="Source A",
        )
    ]


@pytest.mark.asyncio
async def test_llm_as_judge_returns_five_scores():
    response = json.dumps(
        {
            "factuality": 0.85,
            "citation_support": 0.7,
            "completeness": 0.9,
            "reasoning_consistency": 0.8,
            "readability": 0.75,
        }
    )
    llm = MockLLM([response])
    scores = await llm_as_judge(llm, "test question", _report(), _evidence())

    assert set(scores.keys()) == set(JUDGE_DIMENSIONS)
    assert scores["factuality"] == 0.85
    assert scores["citation_support"] == 0.7
    assert all(0.0 <= v <= 1.0 for v in scores.values())


@pytest.mark.asyncio
async def test_llm_as_judge_fallback_on_bad_json():
    llm = MockLLM(["this is not json at all"])
    scores = await llm_as_judge(llm, "test question", _report(), _evidence())

    assert set(scores.keys()) == set(JUDGE_DIMENSIONS)
    assert all(v == 0.5 for v in scores.values())


@pytest.mark.asyncio
async def test_llm_as_judge_clamps_out_of_range():
    response = json.dumps(
        {
            "factuality": 1.5,
            "citation_support": -0.1,
            "completeness": 0.6,
            "reasoning_consistency": 0.5,
            "readability": 0.5,
        }
    )
    llm = MockLLM([response])
    scores = await llm_as_judge(llm, "test question", _report(), _evidence())

    assert scores["factuality"] == 1.0
    assert scores["citation_support"] == 0.0
    assert scores["completeness"] == 0.6
