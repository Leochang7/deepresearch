import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from deepresearch.agents.judge import RoundResult
from deepresearch.core.run_manager import RunManager
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.evaluation.benchmark import (
    BenchmarkCase,
    BenchmarkResult,
    _build_summary,
    load_dataset,
    run_benchmark,
)
from deepresearch.llm.mock import MockLLM
from deepresearch.memory.store import MockMemoryStore
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.mock import MockRetriever
from deepresearch.schemas.evaluation import EvaluationResult
from deepresearch.schemas.report import ReportSection, ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState

_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "bench"
    / "researchbench_mini.jsonl"
)


def test_load_dataset():
    cases = load_dataset(_DATASET_PATH)
    assert len(cases) >= 10
    assert all(isinstance(c, BenchmarkCase) for c in cases)
    assert cases[0].id == "rb-001"
    assert cases[0].domain == "llm_agents"


@pytest.mark.asyncio
async def test_run_benchmark_mock(tmp_path):
    cases = [
        BenchmarkCase(
            id="bench-1",
            domain="test",
            difficulty="easy",
            question="Test question 1",
            expected_facts=["fact1"],
            required_citations=1,
        ),
        BenchmarkCase(
            id="bench-2",
            domain="test",
            difficulty="easy",
            question="Test question 2",
            expected_facts=["fact2"],
            required_citations=1,
        ),
    ]

    def make_manager():
        return RunManager(
            __import__(
                "deepresearch.config", fromlist=["DeepResearchConfig"]
            ).DeepResearchConfig(),
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        )

    results, summary = await run_benchmark(
        cases, make_manager, output_dir=tmp_path / "bench"
    )

    assert len(results) == 2
    assert all(r.run_id for r in results)
    assert (tmp_path / "bench" / "results.jsonl").exists()
    assert (tmp_path / "bench" / "summary.json").exists()

    assert summary["total_cases"] == 2
    assert "avg_task_success_rate" in summary
    assert "per_domain" in summary
    assert "test" in summary["per_domain"]

    results_lines = (
        (tmp_path / "bench" / "results.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    assert len(results_lines) == 2
    first = json.loads(results_lines[0])
    assert first["case_id"] == "bench-1"


@pytest.mark.asyncio
async def test_run_benchmark_fault_isolation_returns_error_result(tmp_path):
    """Single case failure doesn't propagate; error is captured in result."""
    cases = [
        BenchmarkCase(
            id="done",
            domain="test",
            difficulty="easy",
            question="Completed question",
        ),
        BenchmarkCase(
            id="boom",
            domain="test",
            difficulty="easy",
            question="Failing question",
        ),
    ]
    task = TaskNode(task_id="t1", description="task", status=TaskState.SUCCEEDED)
    report = ResearchReport(
        run_id="r1",
        question="Completed question",
        summary="summary",
        sections=[ReportSection(title="Analysis", content="content")],
    )

    class FakeManager:
        calls = 0

        async def run(self, question, *, output_dir):
            output_dir.mkdir(parents=True)
            FakeManager.calls += 1
            if FakeManager.calls == 2:
                raise RuntimeError("case failed")
            return SimpleNamespace(
                run_id="run-done",
                plan_tasks=[task],
                report=report,
                evaluation=EvaluationResult(run_id="run-done"),
                budget=None,
                judge_rounds=[],
            )

    output_dir = tmp_path / "bench"
    results, summary = await run_benchmark(
        cases, lambda: FakeManager(), output_dir=output_dir
    )

    # Fault isolation: all results are returned, including the failed one
    assert len(results) == 2

    done_result = next(r for r in results if r.case_id == "done")
    assert "error" not in done_result.evaluation

    boom_result = next(r for r in results if r.case_id == "boom")
    assert "error" in boom_result.evaluation
    assert boom_result.evaluation["error"] == "case failed"
    assert boom_result.evaluation["stage"] == "run"

    results_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.json"
    assert results_path.exists()
    assert summary_path.exists()
    lines = results_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_summary_includes_difficulty_breakdown():
    results = [
        BenchmarkResult(
            "c1",
            "r1",
            "q1",
            "llm",
            "easy",
            {
                "task_success_rate": 1.0,
                "citation_coverage": 0.8,
                "factual_hit_rate": 0.9,
                "report_section_completeness": 1.0,
            },
            {},
            1.0,
        ),
        BenchmarkResult(
            "c2",
            "r2",
            "q2",
            "rag",
            "hard",
            {
                "task_success_rate": 0.5,
                "citation_coverage": 0.6,
                "factual_hit_rate": 0.5,
                "report_section_completeness": 0.8,
            },
            {},
            2.0,
        ),
    ]
    summary = _build_summary(results, 3.0)
    assert "per_difficulty" in summary
    assert "easy" in summary["per_difficulty"]
    assert "hard" in summary["per_difficulty"]
    assert summary["per_difficulty"]["easy"]["count"] == 1


def test_summary_includes_factual_hit_rate():
    results = [
        BenchmarkResult(
            "c1",
            "r1",
            "q1",
            "d",
            "m",
            {
                "task_success_rate": 1.0,
                "factual_hit_rate": 0.8,
                "hallucination_flag": True,
                "report_section_completeness": 1.0,
                "citation_coverage": 0.9,
            },
            {},
            1.0,
        ),
        BenchmarkResult(
            "c2",
            "r2",
            "q2",
            "d",
            "m",
            {
                "task_success_rate": 0.5,
                "factual_hit_rate": 0.6,
                "hallucination_flag": False,
                "report_section_completeness": 0.8,
                "citation_coverage": 0.7,
            },
            {},
            2.0,
        ),
    ]
    summary = _build_summary(results, 3.0)
    assert summary["avg_factual_hit_rate"] == 0.7
    assert summary["hallucination_flag_count"] == 1


def test_bootstrap_ci_returns_valid_range():
    from deepresearch.evaluation.benchmark import _bootstrap_ci

    values = [0.8, 0.9, 0.7, 0.85, 0.95, 0.6, 0.75]
    ci = _bootstrap_ci(values)
    mean = sum(values) / len(values)
    assert len(ci) == 2
    assert ci[0] <= mean <= ci[1]
    assert ci[0] >= 0.0
    assert ci[1] <= 1.0


@pytest.mark.asyncio
async def test_run_benchmark_recomputes_case_aware_metrics(tmp_path):
    case = BenchmarkCase(
        id="case-aware",
        domain="test",
        difficulty="easy",
        question="What is tested?",
        expected_facts=["alpha fact", "beta fact"],
        required_citations=2,
    )
    evidence = {
        "evidence_id": "E1",
        "task_id": "t1",
        "claim": "alpha fact",
        "quote": "alpha fact quote",
        "citation": "source",
        "confidence": 0.9,
    }
    task = TaskNode(
        task_id="t1",
        description="task",
        status=TaskState.SUCCEEDED,
        result={"evidence": [evidence]},
    )
    report = ResearchReport(
        run_id="r1",
        question=case.question,
        summary="alpha fact and beta fact are both covered [E1].",
        sections=[ReportSection(title="Analysis", content="alpha fact [E1].")],
    )

    class FakeManager:
        async def run(self, question, *, output_dir):
            output_dir.mkdir(parents=True)
            return SimpleNamespace(
                run_id="run-1",
                plan_tasks=[task],
                report=report,
                evaluation=EvaluationResult(
                    run_id="run-1",
                    factual_hit_rate=0.0,
                    judge_scores={"factuality": 0.7},
                ),
                budget=None,
                judge_rounds=[
                    RoundResult(
                        round_num=1,
                        pre_fix_score=0.5,
                        post_fix_score=0.6,
                        issues_count=1,
                        actions_count=1,
                    )
                ],
            )

    results, _summary = await run_benchmark(
        [case],
        lambda: FakeManager(),
        output_dir=tmp_path / "bench",
    )

    assert results[0].evaluation["factual_hit_rate"] == 1.0
    assert results[0].evaluation["hallucination_flag"] is True
    assert results[0].evaluation["red_issue_count"] == 1
    assert results[0].evaluation["blue_fix_count"] == 1
    assert results[0].evaluation["judge_scores"] == {"factuality": 0.7}


@pytest.mark.asyncio
async def test_run_benchmark_uses_manager_llm_for_fact_judge(tmp_path):
    case = BenchmarkCase(
        id="case-judge",
        domain="test",
        difficulty="easy",
        question="What is tested?",
        expected_facts=["semantic coverage fact"],
        required_citations=1,
    )
    evidence = {
        "evidence_id": "E1",
        "task_id": "t1",
        "claim": "semantic coverage",
        "quote": "semantic coverage quote",
        "citation": "source",
        "confidence": 0.9,
    }
    task = TaskNode(
        task_id="t1",
        description="task",
        status=TaskState.SUCCEEDED,
        result={"evidence": [evidence]},
    )
    report = ResearchReport(
        run_id="r1",
        question=case.question,
        summary="The report uses different wording [E1].",
        sections=[ReportSection(title="Analysis", content="Different wording [E1].")],
    )
    llm = MockLLM(
        [
            json.dumps(
                {
                    "verdict": "hit",
                    "supporting_evidence_ids": ["E1"],
                    "reason": "Semantic judge finds the fact covered",
                }
            )
        ]
    )

    class FakeManager:
        def __init__(self) -> None:
            self._llm = llm

        async def run(self, question, *, output_dir):
            output_dir.mkdir(parents=True)
            return SimpleNamespace(
                run_id="run-judge",
                plan_tasks=[task],
                report=report,
                evaluation=EvaluationResult(run_id="run-judge"),
                budget=None,
                judge_rounds=[],
            )

    results, _summary = await run_benchmark(
        [case],
        lambda: FakeManager(),
        output_dir=tmp_path / "bench",
    )

    detail = results[0].evaluation["fact_details"][0]
    assert results[0].evaluation["factual_hit_rate"] == 1.0
    assert detail["source"] == "judge"
    assert detail["supporting_evidence_ids"] == ["E1"]


def test_summary_includes_cohens_d_when_groups_are_available():
    results = [
        BenchmarkResult(
            "e1", "r1", "q", "d", "easy", {"task_success_rate": 1.0}, {}, 1.0
        ),
        BenchmarkResult(
            "e2", "r2", "q", "d", "easy", {"task_success_rate": 0.8}, {}, 1.0
        ),
        BenchmarkResult(
            "h1", "r3", "q", "d", "hard", {"task_success_rate": 0.4}, {}, 1.0
        ),
        BenchmarkResult(
            "h2", "r4", "q", "d", "hard", {"task_success_rate": 0.2}, {}, 1.0
        ),
    ]
    summary = _build_summary(results, 4.0)
    assert summary["cohens_d_easy_vs_hard"] > 0


def test_summary_includes_fact_coverage_distribution():
    results = [
        BenchmarkResult(
            "c1",
            "r1",
            "q1",
            "d",
            "m",
            {
                "task_success_rate": 1.0,
                "factual_hit_rate": 1.0,
                "citation_coverage": 0.9,
                "report_section_completeness": 1.0,
                "fact_details": [
                    {"fact": "f1", "matched": True, "reason": "ok"},
                    {"fact": "f2", "matched": True, "reason": "ok"},
                ],
            },
            {},
            1.0,
        ),
        BenchmarkResult(
            "c2",
            "r2",
            "q2",
            "d",
            "m",
            {
                "task_success_rate": 0.5,
                "factual_hit_rate": 0.0,
                "citation_coverage": 0.5,
                "report_section_completeness": 0.8,
                "fact_details": [
                    {"fact": "f3", "matched": False, "reason": "miss"},
                ],
            },
            {},
            2.0,
        ),
        BenchmarkResult(
            "c3",
            "r3",
            "q3",
            "d",
            "m",
            {
                "task_success_rate": 1.0,
                "factual_hit_rate": 0.5,
                "citation_coverage": 0.8,
                "report_section_completeness": 1.0,
                "fact_details": [
                    {"fact": "f4", "matched": True, "reason": "ok"},
                    {"fact": "f5", "matched": False, "reason": "miss"},
                ],
            },
            {},
            1.5,
        ),
    ]
    summary = _build_summary(results, 4.5)
    dist = summary["fact_coverage_distribution"]
    assert dist["all_hit"] == 1
    assert dist["all_miss"] == 1
    assert dist["partial"] == 1
    assert summary["fact_details_included"] is True


def test_summary_fact_details_included_false_when_no_details():
    results = [
        BenchmarkResult(
            "c1",
            "r1",
            "q1",
            "d",
            "m",
            {
                "task_success_rate": 1.0,
                "factual_hit_rate": 0.0,
                "citation_coverage": 0.9,
                "report_section_completeness": 1.0,
            },
            {},
            1.0,
        )
    ]
    summary = _build_summary(results, 1.0)
    assert summary["fact_details_included"] is False


def test_summary_per_fact_failure_reasons():
    results = [
        BenchmarkResult(
            "c1",
            "r1",
            "q1",
            "d",
            "m",
            {
                "task_success_rate": 1.0,
                "factual_hit_rate": 0.0,
                "citation_coverage": 0.9,
                "report_section_completeness": 1.0,
                "fact_details": [
                    {
                        "fact": "f1",
                        "matched": False,
                        "reason": "Token overlap 1/5 < 50%",
                    },
                    {
                        "fact": "f2",
                        "matched": False,
                        "reason": "Token overlap 0/4 < 50%",
                    },
                ],
            },
            {},
            1.0,
        )
    ]
    summary = _build_summary(results, 1.0)
    failure_reasons = summary["per_fact_failure_reasons"]
    assert len(failure_reasons) > 0
    assert failure_reasons[0]["count"] >= 1


def test_load_dataset_with_dict_format_facts():
    import tempfile

    data = (
        '{"id": "d-1", "domain": "test", "difficulty": "easy", '
        '"question": "q", '
        '"expected_facts": ['
        '{"fact": "fact A", "keywords": ["key1", "key2"]}, '
        '"plain fact B"'
        '], "required_citations": 1, "tags": []}\n'
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        f.write(data)
        tmp_path = Path(f.name)

    try:
        cases = load_dataset(tmp_path)
        assert len(cases) == 1
        assert len(cases[0].expected_facts) == 2
        assert isinstance(cases[0].expected_facts[0], dict)
        assert cases[0].expected_facts[0]["fact"] == "fact A"
        assert isinstance(cases[0].expected_facts[1], str)
    finally:
        tmp_path.unlink()


@pytest.mark.asyncio
async def test_run_benchmark_serial_compatible(tmp_path):
    """max_concurrency=1 produces identical behavior to serial execution (backward compatible)."""
    cases = [
        BenchmarkCase(
            id="s1",
            domain="test",
            difficulty="easy",
            question="What is X?",
            expected_facts=["X is Y"],
            required_citations=1,
            tags=[],
        ),
        BenchmarkCase(
            id="s2",
            domain="test",
            difficulty="hard",
            question="What is Z?",
            expected_facts=["Z is W"],
            required_citations=1,
            tags=[],
        ),
    ]

    def make_manager():
        cfg = __import__(
            "deepresearch.config", fromlist=["DeepResearchConfig"]
        ).DeepResearchConfig()
        return RunManager(
            cfg,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        )

    results, summary = await run_benchmark(
        cases, make_manager, output_dir=tmp_path / "bench", max_concurrency=1
    )

    assert len(results) == 2
    assert results[0].case_id == "s1"
    assert results[1].case_id == "s2"
    assert summary["total_cases"] == 2
    assert "avg_task_success_rate" in summary


@pytest.mark.asyncio
async def test_run_benchmark_concurrent(tmp_path):
    """Cases run concurrently when max_concurrency > 1."""
    import asyncio as _asyncio
    import time

    report = ResearchReport(
        run_id="test",
        question="Q",
        summary="S",
        sections=[ReportSection(title="A", content="B [E1]")],
    )

    class TimedManager:
        async def run(self, question, *, output_dir):
            output_dir.mkdir(parents=True)
            await _asyncio.sleep(0.15)
            return SimpleNamespace(
                run_id="test",
                plan_tasks=[],
                report=report,
                evaluation=EvaluationResult(run_id="test"),
                budget=None,
                judge_rounds=[],
            )

    cases = [
        BenchmarkCase(
            id=f"c{i}",
            domain="test",
            difficulty="easy",
            question=f"Q{i}",
            expected_facts=[],
            required_citations=0,
            tags=[],
        )
        for i in range(4)
    ]

    start = time.monotonic()
    results, summary = await run_benchmark(
        cases,
        lambda: TimedManager(),
        output_dir=tmp_path / "bench",
        max_concurrency=4,
    )
    elapsed = time.monotonic() - start

    assert len(results) == 4
    # 4 cases at 0.15s each with concurrency=4 should take ~0.15s, not ~0.6s
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_run_benchmark_fault_isolation(tmp_path):
    """Single case failure doesn't prevent other cases from completing."""
    report = ResearchReport(
        run_id="test",
        question="Q",
        summary="S",
        sections=[ReportSection(title="A", content="B [E1]")],
    )

    class FailManager:
        async def run(self, question, *, output_dir):
            output_dir.mkdir(parents=True)
            if "fail" in question:
                raise RuntimeError("simulated failure")
            return SimpleNamespace(
                run_id="test",
                plan_tasks=[],
                report=report,
                evaluation=EvaluationResult(run_id="test"),
                budget=None,
                judge_rounds=[],
            )

    cases = [
        BenchmarkCase(
            id="c1",
            domain="test",
            difficulty="easy",
            question="ok1",
            expected_facts=[],
            required_citations=0,
            tags=[],
        ),
        BenchmarkCase(
            id="c2",
            domain="test",
            difficulty="easy",
            question="fail this",
            expected_facts=[],
            required_citations=0,
            tags=[],
        ),
        BenchmarkCase(
            id="c3",
            domain="test",
            difficulty="easy",
            question="ok2",
            expected_facts=[],
            required_citations=0,
            tags=[],
        ),
    ]

    results, _ = await run_benchmark(
        cases,
        lambda: FailManager(),
        output_dir=tmp_path / "bench",
        max_concurrency=3,
    )

    assert len(results) == 3
    c2 = next(r for r in results if r.case_id == "c2")
    assert "error" in c2.evaluation
    c1 = next(r for r in results if r.case_id == "c1")
    assert "error" not in c1.evaluation
    c3 = next(r for r in results if r.case_id == "c3")
    assert "error" not in c3.evaluation


@pytest.mark.asyncio
async def test_run_benchmark_results_in_case_order(tmp_path):
    """Results are ordered by original case order regardless of completion time."""
    import asyncio as _asyncio

    report = ResearchReport(
        run_id="test",
        question="Q",
        summary="S",
        sections=[ReportSection(title="A", content="B [E1]")],
    )

    class VariableSpeedManager:
        async def run(self, question, *, output_dir):
            output_dir.mkdir(parents=True)
            # First case is slow, rest are fast
            delay = 0.2 if "slow" in question else 0.05
            await _asyncio.sleep(delay)
            return SimpleNamespace(
                run_id="test",
                plan_tasks=[],
                report=report,
                evaluation=EvaluationResult(run_id="test"),
                budget=None,
                judge_rounds=[],
            )

    cases = [
        BenchmarkCase(
            id="c-slow",
            domain="test",
            difficulty="easy",
            question="slow query",
            expected_facts=[],
            required_citations=0,
            tags=[],
        ),
        BenchmarkCase(
            id="c-fast1",
            domain="test",
            difficulty="easy",
            question="fast query",
            expected_facts=[],
            required_citations=0,
            tags=[],
        ),
        BenchmarkCase(
            id="c-fast2",
            domain="test",
            difficulty="easy",
            question="fast query",
            expected_facts=[],
            required_citations=0,
            tags=[],
        ),
    ]

    results, _ = await run_benchmark(
        cases,
        lambda: VariableSpeedManager(),
        output_dir=tmp_path / "bench",
        max_concurrency=3,
    )

    assert [r.case_id for r in results] == ["c-slow", "c-fast1", "c-fast2"]
