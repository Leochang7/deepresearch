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
