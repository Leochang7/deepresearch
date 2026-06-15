import json
from unittest.mock import AsyncMock, patch

import pytest

from deepresearch.config import DeepResearchConfig
from deepresearch.core.run_manager import RunManager
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.llm.mock import MockLLM
from deepresearch.memory.store import MockMemoryStore
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.mock import MockRetriever


def _manager(memory: MockMemoryStore | None = None) -> RunManager:
    return RunManager(
        DeepResearchConfig(),
        MockLLM(),
        MockRetriever(),
        memory or MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
    )


@pytest.mark.asyncio
async def test_run_manager_propagates_run_id_and_writes_all_artifacts(tmp_path):
    memory = MockMemoryStore()
    result = await _manager(memory).run(
        "What are the trends in LLM agents?",
        output_dir=tmp_path / "run",
    )

    entries = await memory.snapshot(result.run_id)
    artifact_names = {path.name for path in result.output_dir.iterdir()}

    assert entries
    assert all(entry.run_id == result.run_id for entry in entries)
    assert artifact_names == {
        "report.md",
        "evaluation.json",
        "trace.jsonl",
        "memory_snapshot.jsonl",
    }
    assert (result.output_dir / "memory_snapshot.jsonl").stat().st_size > 0


@pytest.mark.asyncio
async def test_run_manager_produces_grounded_report_and_metrics(tmp_path):
    result = await _manager().run("test question", output_dir=tmp_path / "run")
    report_text = (result.output_dir / "report.md").read_text(encoding="utf-8")

    assert report_text.count("## Executive Summary") == 1
    assert "[E1]" in report_text
    assert "## Analysis" in report_text
    assert result.evaluation.citation_coverage > 0
    assert result.evaluation.empty_citation_rate < 1
    assert result.evaluation.report_section_completeness == 1
    assert result.evaluation.red_issue_count > 0
    assert result.evaluation.blue_fix_count > 0


@pytest.mark.asyncio
async def test_run_manager_trace_covers_pipeline(tmp_path):
    result = await _manager().run("test question", output_dir=tmp_path / "run")
    events = [
        json.loads(line)["event_type"]
        for line in (result.output_dir / "trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert {
        "planner_created_plan",
        "retriever_called",
        "milvus_upserted",
        "llm_called",
        "red_review_created",
        "blue_fix_applied",
        "evaluation_completed",
    } <= set(events)


@pytest.mark.asyncio
async def test_evidence_ids_are_unique_across_tasks(tmp_path):
    result = await _manager().run("test question", output_dir=tmp_path / "run")
    references = result.report.references

    assert len(references) == len(set(references))
    assert len(references) >= 1
    ref = references[0]
    assert "[E1]" in ref and "[E2]" in ref


@pytest.mark.asyncio
async def test_global_timeout_still_writes_partial_outputs(tmp_path):
    config = DeepResearchConfig()
    config.executor.global_timeout_seconds = 0
    manager = RunManager(
        config,
        MockLLM(),
        MockRetriever(),
        MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
    )

    result = await manager.run("test question", output_dir=tmp_path / "run")

    assert (result.output_dir / "report.md").exists()
    assert (result.output_dir / "evaluation.json").exists()
    assert (result.output_dir / "memory_snapshot.jsonl").exists()
    assert any(task.status.value == "CANCELLED" for task in result.plan_tasks)


@pytest.mark.asyncio
async def test_run_manager_passes_fusion_config_to_researcher(tmp_path):
    config = DeepResearchConfig()
    config.fusion.rrf_k = 42
    config.fusion.max_fused_docs = 15
    config.fusion.max_fused_chunks = 25
    config.fusion.mmr_lambda = 0.6
    config.fusion.max_mmr_results = 10

    with patch("deepresearch.core.run_manager.ResearchAgent") as researcher_cls:
        researcher_cls.return_value.execute = AsyncMock(
            return_value={
                "task_id": "t1",
                "queries": [],
                "evidence": [],
                "evidence_count": 0,
                "information_insufficient": True,
                "chunk_count": 0,
                "document_count": 0,
            }
        )
        manager = RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        )

        await manager.run("test question", output_dir=tmp_path / "run")

    kwargs = researcher_cls.call_args.kwargs
    assert kwargs["rrf_k"] == 42
    assert kwargs["max_fused_docs"] == 15
    assert kwargs["max_fused_chunks"] == 25
    assert kwargs["mmr_lambda"] == 0.6
    assert kwargs["max_mmr_results"] == 10
