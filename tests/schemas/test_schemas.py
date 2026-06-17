from deepresearch.schemas.evaluation import (
    BenchmarkCase,
    EvaluationLayers,
    EvaluationResult,
    ExpectedFact,
    FactFailureReason,
    FactHitResult,
)
from deepresearch.schemas.evidence import EvidenceItem, RetrievedDocument
from deepresearch.schemas.report import ReportSection, ResearchReport
from deepresearch.schemas.task import ResearchPlan, TaskNode, TaskState


class TestTaskState:
    def test_all_states_exist(self):
        expected = {
            "PENDING",
            "READY",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
            "SKIPPED",
            "RETRYING",
            "REPLANNING",
            "CANCELLED",
        }
        actual = {s.value for s in TaskState}
        assert actual == expected


class TestTaskNode:
    def test_create_with_defaults(self):
        node = TaskNode(task_id="t1", description="test task")
        assert node.task_id == "t1"
        assert node.status == TaskState.PENDING
        assert node.dependencies == []
        assert node.retries == 0

    def test_with_dependencies(self):
        node = TaskNode(
            task_id="t2",
            description="depends on t1",
            dependencies=["t1"],
        )
        assert node.dependencies == ["t1"]

    def test_with_result(self):
        node = TaskNode(
            task_id="t1",
            description="done",
            status=TaskState.SUCCEEDED,
            result={"summary": "ok"},
        )
        assert node.result == {"summary": "ok"}


class TestResearchPlan:
    def test_create_plan(self):
        tasks = [
            TaskNode(task_id="t1", description="first"),
            TaskNode(task_id="t2", description="second", dependencies=["t1"]),
        ]
        plan = ResearchPlan(
            plan_id="p1",
            question="test question",
            tasks=tasks,
        )
        assert len(plan.tasks) == 2
        assert plan.tasks[1].dependencies == ["t1"]


class TestRetrievedDocument:
    def test_create_with_defaults(self):
        doc = RetrievedDocument(id="d1", title="Test Doc", content="some text")
        assert doc.source_type == "unknown"
        assert doc.url is None

    def test_with_url(self):
        doc = RetrievedDocument(
            id="d1",
            title="Web Doc",
            content="text",
            url="https://example.com",
            source_type="web",
        )
        assert doc.url == "https://example.com"


class TestEvidenceItem:
    def test_create_evidence(self):
        ev = EvidenceItem(
            evidence_id="E1",
            task_id="t1",
            claim="LLM agents are useful",
            quote="LLM agents showed 40% improvement",
            citation="Smith et al. 2024",
            confidence=0.85,
        )
        assert ev.evidence_id == "E1"
        assert ev.confidence == 0.85


class TestResearchReport:
    def test_create_report(self):
        sections = [
            ReportSection(title="Background", content="...", evidence_ids=["E1"]),
        ]
        report = ResearchReport(
            run_id="r1",
            question="test",
            summary="summary",
            sections=sections,
            limitations=["limited data"],
        )
        assert len(report.sections) == 1
        assert report.sections[0].evidence_ids == ["E1"]
        assert report.limitations == ["limited data"]


class TestEvaluationResult:
    def test_create_eval(self):
        result = EvaluationResult(
            run_id="r1",
            task_success_rate=0.9,
            citation_coverage=0.75,
            judge_scores={"accuracy": 0.8, "readability": 0.9},
        )
        assert result.task_success_rate == 0.9
        assert result.judge_scores["accuracy"] == 0.8

    def test_typed_fact_details_keep_dict_style_access(self):
        result = EvaluationResult(
            run_id="r1",
            fact_details=[
                FactHitResult(fact="fact A", matched=True, reason="hit"),
            ],
            per_fact_failure_reasons=[
                FactFailureReason(fact="fact B", reason="miss"),
            ],
        )

        assert result.fact_details[0]["matched"] is True
        assert "fact" in result.per_fact_failure_reasons[0]
        assert result.model_dump(mode="json")["fact_details"][0]["fact"] == "fact A"

    def test_evaluation_layers_keep_backward_compatible_aliases(self):
        result = EvaluationResult(
            run_id="r1",
            task_success_rate=0.8,
            citation_coverage=0.7,
            factual_hit_rate=0.6,
            red_issue_count=2,
            judge_scores={"factuality": 0.9},
            fact_details=[FactHitResult(fact="fact A", matched=True)],
        )

        compatible = result.to_layers().to_compatible_dict()

        assert compatible["rule_metrics"]["task_success_rate"] == 0.8
        assert compatible["statistical_context"]["red_issue_count"] == 2
        assert compatible["task_success_rate"] == 0.8
        assert compatible["judge_scores"]["factuality"] == 0.9
        assert compatible["fact_details"][0]["matched"] is True

    def test_evaluation_layers_parse_flat_dict(self):
        layers = EvaluationLayers.from_evaluation_dict(
            {
                "task_success_rate": 0.8,
                "citation_coverage": 0.7,
                "judge_scores": {"readability": 0.9},
                "fact_details": [{"fact": "fact A", "matched": True}],
                "red_issue_count": 1,
            }
        )

        assert layers.rule_metrics.task_success_rate == 0.8
        assert layers.judge_scores["readability"] == 0.9
        assert layers.statistical_context.fact_details[0].matched is True


class TestBenchmarkCase:
    def test_from_raw_parses_expected_fact_schema(self):
        case = BenchmarkCase.from_raw(
            {
                "id": "c1",
                "domain": "rag",
                "difficulty": "easy",
                "question": "q",
                "expected_facts": [
                    {
                        "fact": "RAG combines retrieval and generation",
                        "aliases": ["RAG"],
                    },
                    "plain fact",
                ],
                "required_citations": 1,
                "tags": ["smoke"],
            }
        )

        assert isinstance(case.expected_facts[0], ExpectedFact)
        assert case.expected_facts[0]["aliases"] == ["RAG"]
        assert case.question_lang == "en"
