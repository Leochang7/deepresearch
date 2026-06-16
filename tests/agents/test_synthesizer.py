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
        retrieved_at="2026-06-16T00:00:00Z",
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
    assert len(report.references) == 1
    ref = report.references[0]
    assert "E1" in ref and "E2" in ref
    assert "Source A" in ref
    assert "https://example.com/source-a" in ref
    assert "2026-06-16T00:00:00Z" in ref


def test_build_evidence_text_includes_source_url():
    text = Synthesizer._build_evidence_text([_evidence()])

    assert "Source URL: https://example.com/source-a" in text


def test_task_summaries_do_not_look_like_citations():
    text = Synthesizer(MockLLM())._build_task_summaries([_task()])

    assert "Task t1:" in text
    assert "[t1]" not in text


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
async def test_markdown_subheadings_do_not_require_citations():
    llm = MockLLM(["## Analysis\n### Retrieval Quality\nSupported [E1]."])

    report = await Synthesizer(llm).synthesize(
        "r1", "question", [_task()], [_evidence()]
    )

    analysis = next(
        section for section in report.sections if section.title == "Analysis"
    )
    assert "### Retrieval Quality" in analysis.content
    assert not any("Retrieval Quality" in item for item in report.limitations)


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


@pytest.mark.asyncio
async def test_references_deduplicated_by_source_url():
    e1 = _evidence("E1")
    e2 = _evidence("E2")
    llm = MockLLM(["## Analysis\nClaim one [E1].\nClaim two [E2]."])

    report = await Synthesizer(llm).synthesize("r1", "q", [_task()], [e1, e2])

    assert len(report.references) == 1
    ref = report.references[0]
    assert "[E1]" in ref and "[E2]" in ref
    assert "Source A" in ref
    assert "https://example.com/source-a" in ref


@pytest.mark.asyncio
async def test_references_local_source_when_url_missing():
    e = EvidenceItem(
        evidence_id="E1",
        task_id="t1",
        claim="local claim",
        quote="local quote",
        citation="",
        source_url=None,
        confidence=0.5,
    )
    llm = MockLLM(["## Analysis\nLocal claim [E1]."])

    report = await Synthesizer(llm).synthesize("r1", "q", [_task()], [e])

    assert len(report.references) == 1
    assert "local source" in report.references[0]


@pytest.mark.asyncio
async def test_references_keep_distinct_local_sources():
    e1 = EvidenceItem(
        evidence_id="E1",
        task_id="t1",
        claim="local claim one",
        quote="local quote one",
        citation="Local Doc A",
        source_url=None,
        confidence=0.8,
        metadata={"document_id": "doc-a"},
    )
    e2 = EvidenceItem(
        evidence_id="E2",
        task_id="t1",
        claim="local claim two",
        quote="local quote two",
        citation="Local Doc B",
        source_url=None,
        confidence=0.8,
        metadata={"document_id": "doc-b"},
    )
    llm = MockLLM(["## Analysis\nOne [E1].\nTwo [E2]."])

    report = await Synthesizer(llm).synthesize("r1", "q", [_task()], [e1, e2])

    assert len(report.references) == 2
    assert any("Local Doc A" in ref for ref in report.references)
    assert any("Local Doc B" in ref for ref in report.references)


@pytest.mark.asyncio
async def test_synthesizer_with_comparison_profile():
    llm = MockLLM(["## Overview\nOverview [E1].\n## Comparison Table\nCompare [E1]."])
    synth = Synthesizer(llm, report_profile="comparison")

    report = await synth.synthesize("r1", "q", [_task()], [_evidence()])

    assert report.sections
    section_titles = {s.title for s in report.sections}
    assert "Comparison Table" in section_titles


def test_synthesizer_prompt_instructs_citing_all_evidence():
    """The synthesizer prompt should tell the LLM to cite all provided evidence."""
    from pathlib import Path
    prompt_path = Path(__file__).resolve().parents[2] / "src" / "deepresearch" / "prompts" / "synthesizer.md"
    content = prompt_path.read_text()
    assert "Cite ALL provided evidence" in content
    assert "multiple evidence items" in content


def test_synthesizer_system_prompt_includes_profile():
    llm = MockLLM()
    synth = Synthesizer(llm, report_profile="timeline")

    assert "timeline" in synth._system_prompt
    assert "Chronological" in synth._system_prompt
    assert "Timeline" in synth._system_prompt
