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

    def test_fact_hit_result_model(self):
        from deepresearch.schemas.evaluation import FactHitResult

        result = FactHitResult(
            fact="test fact",
            matched=True,
            matched_keywords=["test", "fact"],
            unmatched_keywords=[],
            reason="Full phrase match",
            source="rule",
        )
        data = result.model_dump()
        assert data["fact"] == "test fact"
        assert data["matched"] is True
        assert data["source"] == "rule"

    def test_evaluate_fact_with_keyword_groups(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="ReAct is a method that interleaves reasoning steps with actions [E1]",
            sections=[],
        )
        facts = [
            {
                "fact": "ReAct interleaves reasoning and acting steps",
                "keywords": ["ReAct", "reasoning", "acting"],
            }
        ]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.factual_hit_rate == 1.0
        assert result.fact_details[0]["matched"] is True

    def test_evaluate_fact_with_abbreviations(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Large language models are powerful tools for many applications [E1]",
            sections=[],
        )
        facts = ["LLM tools for applications"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.factual_hit_rate == 1.0
        assert result.fact_details[0]["matched"] is True

    def test_evaluate_fact_normalization(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Parameter-Efficient Fine-Tuning (PEFT) reduces memory cost [E1]",
            sections=[],
        )
        facts = ["parameter efficient fine tuning reduces memory cost"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.factual_hit_rate == 1.0

    def test_evaluate_fact_miss(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Some completely unrelated content [E1]",
            sections=[],
        )
        facts = ["quantum computing entanglement superposition"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.factual_hit_rate == 0.0
        assert result.fact_details[0]["matched"] is False
        assert "overlap" in result.fact_details[0]["reason"].lower()

    def test_backward_compatible_list_of_strings(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary with claim 1 and claim 2 and source1",
            sections=[
                ReportSection(
                    title="Analysis",
                    content="Background with claim 1 and source2 [E1]",
                ),
            ],
        )
        facts = ["claim 1", "claim 2", "source1"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.factual_hit_rate == 1.0
        assert len(result.fact_details) == 3

    def test_evaluate_returns_fact_details(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Summary with fact one [E1]",
            sections=[],
        )
        facts = ["fact one", "fact two"]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert len(result.fact_details) == 2
        assert result.fact_details[0]["fact"] == "fact one"
        assert result.fact_details[1]["fact"] == "fact two"

    def test_fact_details_empty_when_no_facts(self, tasks, evidence, report):
        result = evaluate("r1", tasks, report, evidence)
        assert result.fact_details == []

    def test_evaluate_fact_with_aliases(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="Tool use via function calls is supported by modern models [E1]",
            sections=[],
        )
        facts = [
            {
                "fact": "Function calling is supported by OpenAI and Anthropic models",
                "aliases": ["tool use", "function call"],
            }
        ]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert result.fact_details[0]["matched"] is True

    def test_evaluate_fact_with_mixed_formats(self, tasks, evidence):
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="ReAct reasoning acting toolformer self-supervised [E1]",
            sections=[],
        )
        facts: list[str | dict] = [
            "ReAct interleaves reasoning and acting steps",
            {
                "fact": "Function calling is supported by OpenAI and Anthropic",
                "keywords": ["function", "calling"],
            },
        ]
        result = evaluate("r1", tasks, report, evidence, expected_facts=facts)
        assert len(result.fact_details) == 2
        assert result.fact_details[0]["source"] == "rule"


def test_citation_coverage_with_fuzzy_evidence():
    """End-to-end: fuzzy-extracted evidence cited in report body yields high coverage."""
    tasks = [
        TaskNode(
            task_id="t1",
            description="research embeddings",
            status=TaskState.SUCCEEDED,
        ),
    ]
    evidence = [
        EvidenceItem(
            evidence_id="E1",
            task_id="t1",
            claim="embeddings capture semantic meaning",
            quote="embeddings capture semantic meaning",
            confidence=0.8,
        ),
        EvidenceItem(
            evidence_id="E2",
            task_id="t1",
            claim="dense vectors encode text",
            quote="dense vectors encode text into fixed dimensions",
            confidence=0.7,
        ),
        EvidenceItem(
            evidence_id="E3",
            task_id="t1",
            claim="transformers outperform tfidf",
            quote="transformer embeddings outperform TF-IDF",
            confidence=0.75,
        ),
    ]
    report = ResearchReport(
        run_id="test-run",
        question="How do embeddings work?",
        summary="This report covers embeddings [E1] and vectors [E2].",
        sections=[
            ReportSection(
                title="Analysis",
                content=(
                    "Embeddings [E1] capture semantics.\n"
                    "Dense vectors [E2] encode text.\n"
                    "Transformers [E3] outperform older methods."
                ),
            ),
        ],
        references=[],
    )
    result = evaluate("run-1", tasks, report, evidence)
    assert result.citation_coverage >= 0.7
    assert result.hallucination_flag is False


def test_evaluate_fact_chinese_phrase_match():
    from deepresearch.evaluation.metrics import _evaluate_fact

    report_text = "rag（检索增强生成）结合了检索与生成的方法。"
    result = _evaluate_fact("检索增强生成结合检索和生成", report_text)
    assert result.matched is True


def test_evaluate_fact_chinese_keyword_overlap():
    from deepresearch.evaluation.metrics import _evaluate_fact

    report_text = "本文介绍了向量检索和密集检索的原理与应用。"
    spec = {"fact": "密集检索使用向量嵌入进行语义匹配", "keywords": ["密集检索", "向量", "语义"]}
    result = _evaluate_fact(spec, report_text)
    assert result.matched is True


def test_evaluate_fact_chinese_no_match():
    from deepresearch.evaluation.metrics import _evaluate_fact

    report_text = "本文介绍了自然语言处理的基本概念。"
    result = _evaluate_fact("LoRA使用低秩分解微调模型", report_text)
    assert result.matched is False


def test_fact_failure_reason_detects_language_mismatch():
    """Failed Chinese fact against English report should note language mismatch."""
    from deepresearch.evaluation.metrics import _evaluate_fact

    report_text = "this report discusses embeddings in detail."
    spec = {"fact": "检索增强生成结合了检索与生成", "keywords": ["检索", "生成"]}
    result = _evaluate_fact(spec, report_text.lower())
    assert result.matched is False
    assert "language" in result.reason.lower()


def test_fact_failure_reason_no_language_mismatch_when_same_language():
    """English fact against English report should not flag language mismatch."""
    from deepresearch.evaluation.metrics import _evaluate_fact

    report_text = "this report discusses embeddings in detail."
    result = _evaluate_fact("quantum computing entanglement", report_text)
    assert result.matched is False
    assert "language" not in result.reason.lower()


def test_detect_language_chinese():
    from deepresearch.evaluation.metrics import _detect_language

    assert _detect_language("检索增强生成") == "zh"
    assert _detect_language("这是一个测试") == "zh"


def test_detect_language_english():
    from deepresearch.evaluation.metrics import _detect_language

    assert _detect_language("retrieval augmented generation") == "en"
    assert _detect_language("hello world") == "en"
