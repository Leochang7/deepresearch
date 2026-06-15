import json

import pytest

from deepresearch.agents.blue_agent import BlueAgent
from deepresearch.agents.red_agent import RedIssue
from deepresearch.llm.mock import MockLLM
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport


def _report() -> ResearchReport:
    return ResearchReport(
        run_id="r1",
        question="test",
        summary="Original summary.",
        sections=[
            ReportSection(
                title="Background",
                content="Original sentence. Unsupported sentence.",
            )
        ],
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


def _issue() -> RedIssue:
    return RedIssue(
        issue_id="R1",
        type="missing_citation",
        severity="medium",
        location="Background",
        description="Citation missing",
    )


@pytest.mark.asyncio
async def test_add_modify_delete_and_verify_apply_to_report():
    actions = [
        {
            "action_id": "B1",
            "type": "ADD",
            "target": "Background",
            "content": "Added supported sentence.",
            "evidence_id": "E1",
        },
        {
            "action_id": "B2",
            "type": "DELETE",
            "target": "Background",
            "content": "Unsupported sentence.",
        },
        {
            "action_id": "B3",
            "type": "MODIFY",
            "target": "Executive Summary",
            "content": "Revised summary.",
            "evidence_id": "E1",
        },
        {
            "action_id": "B4",
            "type": "VERIFY",
            "target": "Adoption rate",
            "content": "Verify the adoption rate with a primary source.",
        },
    ]
    result = await BlueAgent(MockLLM([json.dumps({"actions": actions})])).fix(
        _report(), [_issue()], _evidence()
    )

    background = result.report.sections[0]
    assert "Added supported sentence. [E1]" in background.content
    assert "Unsupported sentence." not in background.content
    assert result.report.summary == "Revised summary. [E1]"
    assert result.report.limitations == [
        "Verify the adoption rate with a primary source."
    ]
    assert len(result.actions) == 4
    assert result.rejected_actions == []


@pytest.mark.asyncio
async def test_unsafe_or_unresolvable_actions_are_rejected():
    actions = [
        {
            "action_id": "bad-evidence",
            "type": "ADD",
            "target": "Background",
            "content": "Invented claim.",
            "evidence_id": "E999",
        },
        {
            "action_id": "bad-delete",
            "type": "DELETE",
            "target": "Background",
            "content": "Text that is not present.",
        },
        {
            "action_id": "hidden-bad-evidence",
            "type": "MODIFY",
            "target": "Background",
            "content": "Mixed citations [E1] [E999].",
            "evidence_id": "E1",
        },
        {
            "action_id": "bad-type",
            "type": "REWRITE_ALL",
            "target": "Background",
            "content": "Anything",
        },
    ]
    result = await BlueAgent(MockLLM([json.dumps({"actions": actions})])).fix(
        _report(), [_issue()], _evidence()
    )

    assert result.report == _report()
    assert result.actions == []
    assert set(result.rejected_actions) == {
        "bad-evidence",
        "bad-delete",
        "hidden-bad-evidence",
    }


@pytest.mark.asyncio
async def test_bad_json_keeps_original_report():
    report = _report()
    result = await BlueAgent(MockLLM(["not json"])).fix(report, [_issue()], _evidence())

    assert result.report == report
    assert result.actions == []


@pytest.mark.asyncio
async def test_section_suffix_is_normalized_and_duplicate_add_is_rejected():
    action = {
        "action_id": "B1",
        "type": "ADD",
        "target": "Background section",
        "content": "Added supported sentence.",
        "evidence_id": "E1",
    }
    first = await BlueAgent(MockLLM([json.dumps({"actions": [action]})])).fix(
        _report(), [_issue()], _evidence()
    )
    second = await BlueAgent(MockLLM([json.dumps({"actions": [action]})])).fix(
        first.report, [_issue()], _evidence()
    )

    assert len(first.report.sections) == 1
    assert first.report.sections[0].title == "Background"
    assert second.report.sections[0].content.count("Added supported sentence.") == 1
    assert second.rejected_actions == ["B1"]
