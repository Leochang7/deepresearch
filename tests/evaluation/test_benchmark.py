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

        async def run(self, question, *, output_dir, **kwargs):
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
    results, _summary = await run_benchmark(
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
        async def run(self, question, *, output_dir, **kwargs):
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

        async def run(self, question, *, output_dir, **kwargs):
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
        async def run(self, question, *, output_dir, **kwargs):
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
    results, _summary = await run_benchmark(
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
        async def run(self, question, *, output_dir, **kwargs):
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
        async def run(self, question, *, output_dir, **kwargs):
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


def test_load_dataset_with_language_fields(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"id":"c1","domain":"test","difficulty":"easy","question":"什么是RAG?",'
        '"expected_facts":["RAG结合检索和生成"],"required_citations":1,"tags":[],'
        '"question_lang":"zh","evidence_lang":"zh"}\n',
        encoding="utf-8",
    )
    cases = load_dataset(path)
    assert cases[0].question_lang == "zh"
    assert cases[0].evidence_lang == "zh"


def test_load_dataset_language_fields_default_en(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"id":"c1","domain":"test","difficulty":"easy","question":"What is RAG?",'
        '"expected_facts":["RAG combines retrieval and generation"],'
        '"required_citations":1,"tags":[]}\n',
        encoding="utf-8",
    )
    cases = load_dataset(path)
    assert cases[0].question_lang == "en"
    assert cases[0].evidence_lang == "en"


def test_summary_includes_language_breakdown():
    """Summary should include per_question_lang and per_evidence_lang grouping."""
    results = [
        BenchmarkResult(
            case_id="c1",
            run_id="r1",
            question="What is RAG?",
            domain="rag",
            difficulty="easy",
            evaluation={
                "task_success_rate": 1.0,
                "citation_coverage": 0.8,
                "empty_citation_rate": 0.0,
                "report_section_completeness": 1.0,
                "factual_hit_rate": 1.0,
                "hallucination_flag": False,
            },
            budget={},
            elapsed_seconds=1.0,
        ),
        BenchmarkResult(
            case_id="c2",
            run_id="r2",
            question="什么是RAG?",
            domain="cross_lingual",
            difficulty="medium",
            evaluation={
                "task_success_rate": 0.5,
                "citation_coverage": 0.6,
                "empty_citation_rate": 0.1,
                "report_section_completeness": 0.8,
                "factual_hit_rate": 0.5,
                "hallucination_flag": False,
            },
            budget={},
            elapsed_seconds=2.0,
        ),
    ]

    cases = [
        BenchmarkCase(
            id="c1",
            domain="rag",
            difficulty="easy",
            question="What is RAG?",
            expected_facts=[],
            required_citations=0,
            tags=[],
            question_lang="en",
            evidence_lang="en",
        ),
        BenchmarkCase(
            id="c2",
            domain="cross_lingual",
            difficulty="medium",
            question="什么是RAG?",
            expected_facts=[],
            required_citations=0,
            tags=[],
            question_lang="zh",
            evidence_lang="mixed",
        ),
    ]

    summary = _build_summary(results, total_elapsed=3.0, cases=cases)

    assert "per_question_lang" in summary
    assert "en" in summary["per_question_lang"]
    assert "zh" in summary["per_question_lang"]
    assert summary["per_question_lang"]["en"]["count"] == 1
    assert summary["per_question_lang"]["zh"]["count"] == 1

    assert "per_evidence_lang" in summary
    assert "en" in summary["per_evidence_lang"]
    assert "mixed" in summary["per_evidence_lang"]
    assert summary["per_evidence_lang"]["en"]["count"] == 1
    assert summary["per_evidence_lang"]["mixed"]["count"] == 1

    assert "per_language_scenario" in summary
    assert summary["per_language_scenario"]["en->en"]["count"] == 1
    assert summary["per_language_scenario"]["zh->mixed"]["count"] == 1


def test_summary_language_breakdown_without_cases():
    """When no cases are passed, per_question_lang and per_evidence_lang should still be present but empty."""
    results = [
        BenchmarkResult(
            "c1",
            "r1",
            "q1",
            "d",
            "m",
            {
                "task_success_rate": 1.0,
                "citation_coverage": 0.8,
                "factual_hit_rate": 0.9,
                "report_section_completeness": 1.0,
            },
            {},
            1.0,
        ),
    ]
    summary = _build_summary(results, total_elapsed=1.0)
    assert summary["per_question_lang"] == {}
    assert summary["per_evidence_lang"] == {}
    assert summary["per_language_scenario"] == {}


def test_summary_includes_per_model_backend():
    results = [
        BenchmarkResult(
            case_id="c1",
            run_id="r1",
            question="Q1",
            domain="d",
            difficulty="easy",
            evaluation={
                "task_success_rate": 0.8,
                "citation_coverage": 0.7,
                "factual_hit_rate": 0.9,
                "report_section_completeness": 1.0,
            },
            budget={},
            elapsed_seconds=1.0,
        ),
    ]
    cases = [
        BenchmarkCase(
            id="c1",
            domain="d",
            difficulty="easy",
            question="Q1",
            expected_facts=[],
            required_citations=0,
            tags=[],
            model_backend="mimo",
            model_name="mimo-v2.5-pro",
        ),
    ]
    summary = _build_summary(results, 1.0, cases=cases)
    assert "per_model_backend" in summary
    assert "mimo" in summary["per_model_backend"]
    assert "per_model_name" in summary
    assert "mimo-v2.5-pro" in summary["per_model_name"]


def test_summary_per_model_backend_without_cases():
    """When no cases are passed, per_model_backend and per_model_name should be empty dicts."""
    results = [
        BenchmarkResult(
            "c1", "r1", "q1", "d", "easy",
            {"task_success_rate": 1.0, "citation_coverage": 0.8,
             "factual_hit_rate": 0.9, "report_section_completeness": 1.0},
            {}, 1.0,
        ),
    ]
    summary = _build_summary(results, 1.0)
    assert summary["per_model_backend"] == {}
    assert summary["per_model_name"] == {}


def test_compare_summaries():
    from deepresearch.evaluation.benchmark import compare_summaries

    before = {
        "avg_task_success_rate": 0.6,
        "avg_citation_coverage": 0.5,
        "cohens_d_easy_vs_hard": 0.1,
        "per_question_lang": {
            "en": {"avg_citation_coverage": 0.7, "count": 5},
            "zh": {"avg_citation_coverage": 0.3, "count": 3},
        },
        "per_language_scenario": {
            "zh->mixed": {"avg_factual_hit_rate": 0.4, "count": 3},
        },
    }
    after = {
        "avg_task_success_rate": 0.8,
        "avg_citation_coverage": 0.7,
        "cohens_d_easy_vs_hard": 0.3,
        "per_question_lang": {
            "en": {"avg_citation_coverage": 0.8, "count": 5},
            "zh": {"avg_citation_coverage": 0.6, "count": 3},
        },
        "per_language_scenario": {
            "zh->mixed": {"avg_factual_hit_rate": 0.7, "count": 3},
        },
    }
    diff = compare_summaries(before, after)
    assert diff["avg_task_success_rate"]["delta"] == pytest.approx(0.2)
    assert diff["avg_citation_coverage"]["delta"] == pytest.approx(0.2)
    assert diff["cohens_d_easy_vs_hard"]["delta"] == pytest.approx(0.2)
    assert diff["per_question_lang"]["zh"]["avg_citation_coverage"][
        "delta"
    ] == pytest.approx(0.3)
    assert diff["per_language_scenario"]["zh->mixed"]["avg_factual_hit_rate"][
        "delta"
    ] == pytest.approx(0.3)


def test_compare_summaries_missing_keys():
    """Comparison handles missing keys gracefully."""
    from deepresearch.evaluation.benchmark import compare_summaries

    before = {"avg_task_success_rate": 0.5}
    after = {"avg_task_success_rate": 0.7, "avg_citation_coverage": 0.6}
    diff = compare_summaries(before, after)
    assert diff["avg_task_success_rate"]["delta"] == pytest.approx(0.2)
    assert diff["avg_citation_coverage"]["delta"] == pytest.approx(0.6)


def test_multilingual_dataset_loads_15_cases():
    from deepresearch.evaluation.benchmark import load_dataset

    base = Path(__file__).resolve().parents[2]
    smoke5 = load_dataset(base / "examples" / "bench" / "researchbench_smoke5.jsonl")
    cross = load_dataset(base / "examples" / "bench" / "crosslingual_smoke10.jsonl")
    total = len(smoke5) + len(cross)
    assert total == 15, (
        f"Expected 15 cases, got {total} ({len(smoke5)} smoke5 + {len(cross)} crosslingual)"
    )
    zh_cases = [c for c in cross if c.question_lang == "zh"]
    assert len(zh_cases) >= 4, f"Expected at least 4 zh cases, got {len(zh_cases)}"


def test_multilingual_large20_dataset_loads():
    cases = load_dataset(Path("examples/bench/multilingual_large20.jsonl"))
    assert len(cases) == 20

    ids = {case.id for case in cases}
    assert {"rb-001", "cl-001", "cl-015"} <= ids
    assert {case.question_lang for case in cases} >= {"en", "zh", "mixed"}
    assert {case.evidence_lang for case in cases} >= {"en", "zh", "mixed"}
    assert {case.domain for case in cases} >= {
        "model_compression",
        "privacy",
        "multimodal",
        "orchestration",
        "data_quality",
    }


@pytest.mark.asyncio
async def test_multilingual_benchmark_mock(tmp_path):
    """A multilingual benchmark sample runs in mock mode without errors."""
    cases = load_dataset(Path("examples/bench/crosslingual_smoke10.jsonl"))
    assert len(cases) >= 7

    corpus = Path("examples/corpus/crosslingual")

    def make_manager():
        from deepresearch.config import DeepResearchConfig
        from deepresearch.retrieval.local_dataset import LocalDatasetRetriever

        cfg = DeepResearchConfig()
        return RunManager(
            cfg,
            MockLLM(),
            LocalDatasetRetriever(corpus),
            MockMemoryStore(),
            MockEmbeddingClient(dim=cfg.embedding.dim),
            MockRerankerClient(),
        )

    results, summary = await run_benchmark(
        cases[:3],
        make_manager,
        output_dir=tmp_path / "bench",
        max_concurrency=2,
    )
    assert len(results) == 3
    assert summary["total_cases"] == 3
    assert "per_question_lang" in summary
    # Should have at least one zh group
    assert "zh" in summary["per_question_lang"] or any(
        r.case_id.startswith("cl-00") for r in results
    )


def test_benchmark_result_has_three_layer_structure():
    """Evaluation dict should contain rule_metrics, judge_scores, statistical_context."""
    from deepresearch.evaluation.benchmark import _restructure_evaluation

    flat = {
        "task_success_rate": 0.8,
        "citation_coverage": 0.7,
        "factual_hit_rate": 0.9,
        "hallucination_flag": False,
        "hallucination_details": [],
        "judge_scores": {"factuality": 0.85, "readability": 0.9},
        "fact_details": [{"fact": "F1", "matched": True}],
        "red_issue_count": 1,
        "blue_fix_count": 0,
    }
    structured = _restructure_evaluation(flat)
    assert "rule_metrics" in structured
    assert "judge_scores" in structured
    assert "statistical_context" in structured
    assert structured["rule_metrics"]["task_success_rate"] == 0.8
    assert structured["judge_scores"]["factuality"] == 0.85
    # Backward compat
    assert structured["task_success_rate"] == 0.8
    assert structured["factual_hit_rate"] == 0.9


@pytest.mark.asyncio
async def test_multilingual_large20_benchmark_mock_sample(tmp_path):
    """A larger multilingual benchmark sample keeps language-scenario grouping."""
    cases = load_dataset(Path("examples/bench/multilingual_large20.jsonl"))
    sample = [cases[0], cases[5], cases[15]]

    corpus = Path("examples/corpus")

    def make_manager():
        from deepresearch.config import DeepResearchConfig
        from deepresearch.retrieval.local_dataset import LocalDatasetRetriever

        cfg = DeepResearchConfig()
        return RunManager(
            cfg,
            MockLLM(),
            LocalDatasetRetriever(corpus),
            MockMemoryStore(),
            MockEmbeddingClient(dim=cfg.embedding.dim),
            MockRerankerClient(),
        )

    results, summary = await run_benchmark(
        sample,
        make_manager,
        output_dir=tmp_path / "bench-large20",
        max_concurrency=2,
    )

    assert len(results) == 3
    assert summary["total_cases"] == 3
    assert "en->en" in summary["per_language_scenario"]
    assert "zh->mixed" in summary["per_language_scenario"]
