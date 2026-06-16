import json

import pytest

from deepresearch.evaluation.judge_eval import (
    JUDGE_DIMENSIONS,
    judge_facts,
    llm_as_judge,
)
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

    assert set(JUDGE_DIMENSIONS).issubset(scores.keys())
    assert all(v == 0.5 for dim, v in scores.items() if dim in JUDGE_DIMENSIONS)
    assert "__failure_reason" in scores


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


# --- judge_facts tests ---


@pytest.mark.asyncio
async def test_judge_facts_hit_verdict():
    fact_details = [
        {
            "fact": "Embeddings capture semantic meaning",
            "matched": False,
            "matched_keywords": ["semantic"],
            "unmatched_keywords": ["embeddings", "capture", "meaning"],
            "reason": "Token overlap 1/4 < 50%",
            "source": "rule",
        }
    ]
    judge_response = json.dumps(
        {
            "verdict": "hit",
            "supporting_evidence_ids": ["E1"],
            "reason": "Report discusses embedding semantic representations",
        }
    )
    llm = MockLLM([judge_response])
    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert len(result) == 1
    assert result[0]["matched"] is True
    assert result[0]["source"] == "judge"
    assert "[judge:hit]" in result[0]["reason"]
    assert result[0]["supporting_evidence_ids"] == ["E1"]


@pytest.mark.asyncio
async def test_judge_facts_miss_verdict():
    fact_details = [
        {
            "fact": "Quantum computing uses qubits",
            "matched": False,
            "matched_keywords": [],
            "unmatched_keywords": ["quantum", "computing", "qubits"],
            "reason": "No overlap",
            "source": "rule",
        }
    ]
    judge_response = json.dumps(
        {
            "verdict": "miss",
            "supporting_evidence_ids": [],
            "reason": "Report does not discuss quantum computing",
        }
    )
    llm = MockLLM([judge_response])
    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert result[0]["matched"] is False
    assert result[0]["source"] == "judge"
    assert "[judge:miss]" in result[0]["reason"]


@pytest.mark.asyncio
async def test_llm_as_judge_returns_failure_reason_on_bad_json():
    llm = MockLLM(["this is not json at all"])
    scores = await llm_as_judge(llm, "test question", _report(), _evidence())

    assert set(scores.keys()) == set(JUDGE_DIMENSIONS) | {"__failure_reason"}
    assert all(v == 0.5 for k, v in scores.items() if k != "__failure_reason")
    assert "parse" in scores["__failure_reason"].lower() or scores["__failure_reason"] != ""


@pytest.mark.asyncio
async def test_llm_as_judge_returns_failure_reason_on_non_dict():
    llm = MockLLM(['"just a string"'])
    scores = await llm_as_judge(llm, "test question", _report(), _evidence())

    assert "__failure_reason" in scores
    assert all(v == 0.5 for k, v in scores.items() if k != "__failure_reason")


@pytest.mark.asyncio
async def test_llm_as_judge_no_failure_reason_on_success():
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

    assert "__failure_reason" not in scores


@pytest.mark.asyncio
async def test_llm_as_judge_failure_reason_on_exception():
    class FailingLLM(MockLLM):
        async def chat(self, messages, json_mode=False):
            raise RuntimeError("API timeout")

    llm = FailingLLM([])
    scores = await llm_as_judge(llm, "test question", _report(), _evidence())

    assert "__failure_reason" in scores
    assert "API timeout" in scores["__failure_reason"]


@pytest.mark.asyncio
async def test_judge_facts_fallback_on_llm_failure():
    fact_details = [
        {
            "fact": "Some fact",
            "matched": False,
            "matched_keywords": [],
            "unmatched_keywords": ["some", "fact"],
            "reason": "No overlap",
            "source": "rule",
        }
    ]

    class FailingLLM(MockLLM):
        async def chat(self, messages, json_mode=False):
            raise RuntimeError("API error")

    llm = FailingLLM([])
    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert len(result) == 1
    assert result[0]["matched"] is False
    assert result[0]["source"] == "rule"
    assert result[0]["reason"] == "No overlap"


@pytest.mark.asyncio
async def test_judge_facts_skips_already_matched():
    fact_details = [
        {
            "fact": "Already matched fact",
            "matched": True,
            "matched_keywords": ["already", "matched", "fact"],
            "unmatched_keywords": [],
            "reason": "Full phrase match",
            "source": "rule",
        }
    ]
    # No LLM call expected — MockLLM will error if called
    llm = MockLLM([])

    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert len(result) == 1
    assert result[0]["matched"] is True
    assert result[0]["source"] == "rule"


@pytest.mark.asyncio
async def test_judge_facts_uncertain_verdict():
    fact_details = [
        {
            "fact": "Partially supported claim",
            "matched": False,
            "matched_keywords": [],
            "unmatched_keywords": ["partially", "supported", "claim"],
            "reason": "No overlap",
            "source": "rule",
        }
    ]
    judge_response = json.dumps(
        {
            "verdict": "uncertain",
            "supporting_evidence_ids": ["E1"],
            "reason": "Evidence partially addresses this but is inconclusive",
        }
    )
    llm = MockLLM([judge_response])
    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert result[0]["matched"] is False
    assert result[0]["source"] == "judge"
    assert "[judge:uncertain]" in result[0]["reason"]


@pytest.mark.asyncio
async def test_judge_facts_filters_unknown_evidence_ids():
    fact_details = [
        {
            "fact": "Supported claim",
            "matched": False,
            "matched_keywords": [],
            "unmatched_keywords": ["supported", "claim"],
            "reason": "No overlap",
            "source": "rule",
        }
    ]
    judge_response = json.dumps(
        {
            "verdict": "hit",
            "supporting_evidence_ids": ["E1", "E999"],
            "reason": "Only E1 exists in the evidence list",
        }
    )
    llm = MockLLM([judge_response])

    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert result[0]["matched"] is True
    assert result[0]["supporting_evidence_ids"] == ["E1"]


@pytest.mark.asyncio
async def test_judge_facts_fallback_on_invalid_verdict():
    fact_details = [
        {
            "fact": "Some fact",
            "matched": False,
            "matched_keywords": [],
            "unmatched_keywords": ["some", "fact"],
            "reason": "No overlap",
            "source": "rule",
        }
    ]
    llm = MockLLM([json.dumps({"result": "ok"})])

    result = await judge_facts(
        llm, "test question", _report(), _evidence(), fact_details
    )

    assert result[0]["matched"] is False
    assert result[0]["source"] == "rule"
    assert result[0]["reason"] == "No overlap"
