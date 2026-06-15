import json
from pathlib import Path

import pytest

from deepresearch.core.run_manager import RunManager
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.evaluation.benchmark import (
    BenchmarkCase,
    load_dataset,
    run_benchmark,
)
from deepresearch.llm.mock import MockLLM
from deepresearch.memory.store import MockMemoryStore
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.mock import MockRetriever

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
