import json

import pytest

from deepresearch.agents.blue_agent import BlueAgent
from deepresearch.agents.judge import Judge, JudgeConfig, RoundResult
from deepresearch.agents.red_agent import RedAgent
from deepresearch.llm.mock import MockLLM
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport


def _report() -> ResearchReport:
    return ResearchReport(
        run_id="r1",
        question="test",
        sections=[ReportSection(title="Analysis", content="Unsupported claim.")],
    )


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            evidence_id="E1",
            task_id="t1",
            claim="Supported claim",
            quote="Supporting quote",
            citation="Source A",
        )
    ]


def _review(score: float, *, issue: bool = True) -> str:
    issues = []
    if issue:
        issues.append(
            {
                "issue_id": "R1",
                "type": "missing_citation",
                "severity": "high",
                "location": "Analysis",
                "description": "Missing citation",
                "suggestion": "Add supported evidence",
            }
        )
    return json.dumps({"issues": issues, "score": score})


def _fix() -> str:
    return json.dumps(
        {
            "actions": [
                {
                    "action_id": "B1",
                    "type": "MODIFY",
                    "target": "Analysis",
                    "content": "Supported claim.",
                    "evidence_id": "E1",
                }
            ]
        }
    )


def _judge(red_responses: list[str], blue_responses: list[str], **config) -> Judge:
    return Judge(
        JudgeConfig(**config),
        red_agent=RedAgent(MockLLM(red_responses)),
        blue_agent=BlueAgent(MockLLM(blue_responses)),
    )


@pytest.mark.asyncio
async def test_run_executes_fix_and_stops_on_red_review_target():
    judge = _judge(
        [_review(0.5), _review(0.9, issue=False)],
        [_fix()],
        max_rounds=3,
        target_score=0.85,
    )

    result = await judge.run(_report(), _evidence())

    assert result.final_score == 0.9
    assert result.termination_reason.startswith("target score reached")
    assert result.report.sections[0].content == "Supported claim. [E1]"
    assert len(result.rounds) == 1
    assert result.rounds[0].pre_fix_score == 0.5
    assert result.rounds[0].post_fix_score == 0.9


@pytest.mark.asyncio
async def test_blue_self_score_cannot_terminate_loop():
    blue_response = json.dumps({"actions": [], "revised_score": 1.0})
    judge = _judge(
        [
            _review(0.4, issue=False),
            _review(0.5, issue=False),
            _review(0.55, issue=False),
            _review(0.6, issue=False),
        ],
        [blue_response, blue_response, blue_response],
        max_rounds=3,
        target_score=0.85,
        min_score_delta=0.01,
    )

    result = await judge.run(_report(), _evidence())

    assert result.final_score == 0.6
    assert result.termination_reason == "max rounds (3) reached"


def test_repeated_issue_signature_stops_as_oscillation():
    judge = Judge(JudgeConfig(max_rounds=3, oscillation_window=2))
    signature = {"missing_citation:analysis"}
    judge.record_round(RoundResult(1, 0.5, 0.6, 1, 1, signature))
    judge.record_round(RoundResult(2, 0.6, 0.7, 1, 1, signature))

    should_continue, reason = judge.should_continue()

    assert should_continue is False
    assert reason == "issue oscillation detected"


def test_two_small_improvements_stop_as_converged():
    judge = Judge(JudgeConfig(max_rounds=3, min_score_delta=0.03, oscillation_window=2))
    judge.record_round(RoundResult(1, 0.50, 0.51, 1, 1, {"a:x"}))
    judge.record_round(RoundResult(2, 0.51, 0.52, 1, 1, {"b:y"}))

    should_continue, reason = judge.should_continue()

    assert should_continue is False
    assert "converged" in reason


def test_default_config_and_empty_final_report():
    config = JudgeConfig()
    assert config.max_rounds == 3
    assert config.target_score == 0.85
    assert config.min_score_delta == 0.03
    assert config.oscillation_window == 2
    assert Judge().final_report()["rounds"] == 0
