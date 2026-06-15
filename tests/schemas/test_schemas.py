from deepresearch.schemas.evaluation import EvaluationResult
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
