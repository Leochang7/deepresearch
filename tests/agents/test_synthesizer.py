import pytest

from deepresearch.agents.synthesizer import Synthesizer
from deepresearch.llm.mock import MockLLM
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState


def _evidence(evidence_id: str = "E1") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        task_id="t1",
        claim="Test claim",
        quote="Test quote",
        citation="Source A",
        source_url="https://example.com/source-a",
        confidence=0.9,
    )


def _task(status: TaskState = TaskState.SUCCEEDED) -> TaskNode:
    return TaskNode(task_id="t1", description="test task", status=status)


@pytest.mark.asyncio
async def test_synthesize_returns_cited_report_with_full_evidence_ids():
    report = await Synthesizer(MockLLM()).synthesize(
        "r1", "test question", [_task()], [_evidence("E1"), _evidence("E2")]
    )

    assert isinstance(report, ResearchReport)
    assert report.summary
    assert report.sections
    assert {evidence_id for s in report.sections for evidence_id in s.evidence_ids} == {
        "E1",
        "E2",
    }
    assert not any("Unused evidence" in item for item in report.limitations)
    assert len(report.references) == 2
    assert report.references[0] == "[E1] Source A - https://example.com/source-a"


def test_build_evidence_text_includes_source_url():
    text = Synthesizer._build_evidence_text([_evidence()])

    assert "Source URL: https://example.com/source-a" in text


@pytest.mark.asyncio
async def test_unknown_citation_is_removed_and_added_to_limitations():
    llm = MockLLM(
        [
            (
                "## Analysis\n"
                "Known claim [E1].\n"
                "Invented claim [E999].\n\n"
                "## Limitations\nModel-provided caveat."
            )
        ]
    )

    report = await Synthesizer(llm).synthesize(
        "r1", "question", [_task()], [_evidence()]
    )

    analysis = next(
        section for section in report.sections if section.title == "Analysis"
    )
    assert "Known claim [E1]." in analysis.content
    assert "E999" not in analysis.content
    assert any("Unsupported claim" in item for item in report.limitations)
    assert "Model-provided caveat." in report.limitations


@pytest.mark.asyncio
async def test_uncited_claim_is_moved_to_limitations():
    llm = MockLLM(["## Analysis\nSupported [E1].\nUnsupported factual claim."])

    report = await Synthesizer(llm).synthesize(
        "r1", "question", [_task()], [_evidence()]
    )

    analysis = next(
        section for section in report.sections if section.title == "Analysis"
    )
    assert analysis.content == "Supported [E1]."
    assert any(
        item == "Uncited claim in Analysis: Unsupported factual claim."
        for item in report.limitations
    )


@pytest.mark.asyncio
async def test_failed_tasks_and_unused_evidence_are_limitations():
    llm = MockLLM(["## Analysis\nOnly first source is used [E1]."])

    report = await Synthesizer(llm).synthesize(
        "r1",
        "question",
        [_task(TaskState.FAILED)],
        [_evidence("E1"), _evidence("E2")],
    )

    assert "Failed tasks: t1" in report.limitations
    assert "Unused evidence: E2" in report.limitations
