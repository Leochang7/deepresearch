import pytest

from deepresearch.evaluation.metrics import evaluate
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState


class TestEvaluator:
    @pytest.fixture
    def tasks(self):
        return [
            TaskNode(task_id="t1", description="task 1", status=TaskState.SUCCEEDED),
            TaskNode(task_id="t2", description="task 2", status=TaskState.SUCCEEDED),
            TaskNode(task_id="t3", description="task 3", status=TaskState.FAILED),
        ]

    @pytest.fixture
    def evidence(self):
        return [
            EvidenceItem(
                evidence_id="E1",
                task_id="t1",
                claim="claim 1",
                quote="q1",
                citation="src1",
                confidence=0.9,
            ),
            EvidenceItem(
                evidence_id="E2",
                task_id="t2",
                claim="claim 2",
                quote="q2",
                citation="src2",
                confidence=0.8,
            ),
        ]

    @pytest.fixture
    def report(self):
        return ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary with [E1] reference",
            sections=[
                ReportSection(title="Executive Summary", content="Summary text"),
                ReportSection(title="Background", content="Background with [E1]"),
                ReportSection(title="Analysis", content="Analysis with [E2]"),
                ReportSection(title="Limitations", content="Some limitations"),
                ReportSection(title="References", content="[E1] src1\n[E2] src2"),
            ],
            limitations=["Limited"],
        )

    def test_task_success_rate(self, tasks, evidence, report):
        result = evaluate("r1", tasks, report, evidence)
        assert result.task_success_rate == pytest.approx(0.6667, abs=1e-3)

    def test_task_success_rate_excludes_superseded_tasks(self, tasks, evidence, report):
        tasks[2].status = TaskState.REPLANNING
        tasks.append(
            TaskNode(
                task_id="replan-1-t3",
                description="replacement",
                status=TaskState.SUCCEEDED,
            )
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.task_success_rate == 1.0

    def test_citation_coverage(self, tasks, evidence, report):
        result = evaluate("r1", tasks, report, evidence)
        assert result.citation_coverage == pytest.approx(1.0)

    def test_citation_coverage_partial(self, tasks, evidence):
        evidence.append(
            EvidenceItem(
                evidence_id="E3",
                task_id="t3",
                claim="unused",
                quote="q3",
                citation="src3",
            )
        )
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="",
            sections=[ReportSection(title="Analysis", content="[E1] only")],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.citation_coverage < 1.0

    def test_references_do_not_inflate_body_citation_coverage(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="No citation in the body.",
            sections=[ReportSection(title="Analysis", content="Still no citation.")],
            references=["[E1] src1", "[E2] src2"],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.citation_coverage == 0.0

    def test_empty_citation_rate(self, tasks, evidence, report):
        result = evaluate("r1", tasks, report, evidence)
        assert result.empty_citation_rate < 1.0

    def test_report_section_completeness(self, tasks, evidence, report):
        result = evaluate("r1", tasks, report, evidence)
        assert result.report_section_completeness == pytest.approx(1.0)

    def test_report_section_completeness_partial(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="",
            sections=[ReportSection(title="Analysis", content="text")],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.report_section_completeness < 1.0

    def test_separate_summary_limitations_and_references_count_as_sections(
        self, tasks, evidence
    ):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary [E1].",
            sections=[
                ReportSection(title="Background", content="Background [E1]."),
                ReportSection(title="Analysis", content="Analysis [E2]."),
            ],
            limitations=["Limited scope"],
            references=["[E1] src1", "[E2] src2"],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.report_section_completeness == 1.0

    def test_section_completeness_is_case_insensitive(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary [E1].",
            sections=[
                ReportSection(title="background", content="Background [E1]."),
                ReportSection(title="ANALYSIS", content="Analysis [E2]."),
            ],
            limitations=["Limited scope"],
            references=["[E1] src1"],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.report_section_completeness == 1.0

    def test_red_blue_counts(self, tasks, evidence, report):
        red_issues = [{"id": "R1"}, {"id": "R2"}]
        blue_actions = [{"id": "B1"}]
        result = evaluate(
            "r1",
            tasks,
            report,
            evidence,
            red_issues=red_issues,
            blue_actions=blue_actions,
        )
        assert result.red_issue_count == 2
        assert result.blue_fix_count == 1

    def test_no_evidence(self, tasks):
        report = ResearchReport(run_id="r1", question="test", summary="", sections=[])
        result = evaluate("r1", tasks, report, [])
        assert result.citation_coverage == 0.0
        assert result.empty_citation_rate == 1.0

    def test_factual_hit_rate_all_found(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary with claim 1 and claim 2 and source1",
            sections=[
                ReportSection(
                    title="Analysis", content="Background with claim 1 and source2 [E1]"
                ),
            ],
        )
        facts = ["claim 1", "claim 2", "source1"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.factual_hit_rate == 1.0

    def test_factual_hit_rate_partial(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary with claim 1 [E1]",
            sections=[],
        )
        facts = ["claim 1", "nonexistent fact xyz", "another missing fact"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert 0.3 <= result.factual_hit_rate <= 0.4

    def test_hallucination_flag_when_many_uncited(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary",
            sections=[
                ReportSection(title="Background", content="Uncited claim here."),
                ReportSection(title="Analysis", content="Another uncited claim."),
                ReportSection(title="Executive Summary", content="Summary text [E1]"),
            ],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.hallucination_flag is True
        assert len(result.hallucination_details) > 0

    def test_hallucination_flag_false_when_well_cited(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary [E1]",
            sections=[
                ReportSection(title="Background", content="Background [E1]"),
                ReportSection(title="Analysis", content="Analysis [E2]"),
            ],
        )
        result = evaluate("r1", tasks, report, evidence)
        assert result.hallucination_flag is False
        assert result.hallucination_details == []

    def test_required_citations_can_trigger_hallucination_flag(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary [E1]",
            sections=[ReportSection(title="Analysis", content="Analysis [E1]")],
        )
        result = evaluate(
            "r1",
            tasks,
            report,
            evidence,
            required_citations=2,
        )
        assert result.hallucination_flag is True
        assert "required at least 2" in result.hallucination_details[-1]
