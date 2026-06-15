import pytest

from deepresearch.agents.red_agent import RedAgent
from deepresearch.llm.mock import MockLLM
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport


def _report() -> ResearchReport:
    return ResearchReport(
        run_id="r1",
        question="test question",
        summary="Summary [E1].",
        sections=[ReportSection(title="Analysis", content="Claim [E1].")],
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
async def test_review_returns_validated_issues_and_score():
    llm = MockLLM(
        [
            (
                '{"issues": [{"issue_id": "R1", "type": "missing_citation", '
                '"severity": "medium", "location": "Analysis", '
                '"description": "No citation", "suggestion": "Add one"}], '
                '"score": 0.7}'
            )
        ]
    )

    result = await RedAgent(llm).review(_report(), _evidence())

    assert result.score == 0.7
    assert result.issues[0].signature == "missing_citation:analysis"


@pytest.mark.asyncio
async def test_review_drops_invalid_issues_and_clamps_score():
    llm = MockLLM(
        [
            (
                '{"issues": [{"issue_id": "R1", "type": "made_up", '
                '"severity": "critical", "location": "x", "description": "x"}], '
                '"score": 5}'
            )
        ]
    )

    result = await RedAgent(llm).review(_report(), _evidence())

    assert result.issues == []
    assert result.score == 1.0


@pytest.mark.asyncio
async def test_review_bad_json_returns_safe_default():
    result = await RedAgent(MockLLM(["not json"])).review(_report(), _evidence())

    assert result.issues == []
    assert result.score == 0.5
