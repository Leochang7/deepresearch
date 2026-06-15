import json

import pytest

from deepresearch.config import DeepResearchConfig
from deepresearch.core.run_manager import RunManager
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.llm.mock import MockLLM
from deepresearch.memory.store import MockMemoryStore
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.mock import MockRetriever


def _make_manager() -> RunManager:
    return RunManager(
        DeepResearchConfig(),
        MockLLM(),
        MockRetriever(),
        MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
    )


@pytest.mark.asyncio
async def test_mock_pipeline_is_offline_and_produces_meaningful_outputs(tmp_path):
    result = await _make_manager().run(
        "What are the trends in LLM agents?",
        output_dir=tmp_path / "run",
    )

    report = (result.output_dir / "report.md").read_text(encoding="utf-8")
    evaluation = json.loads(
        (result.output_dir / "evaluation.json").read_text(encoding="utf-8")
    )
    snapshot_lines = (
        (result.output_dir / "memory_snapshot.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    trace_lines = (
        (result.output_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    )

    assert result.run_id
    assert "## Analysis" in report
    assert "[E1]" in report
    assert evaluation["citation_coverage"] > 0
    assert evaluation["report_section_completeness"] == 1
    assert snapshot_lines
    assert all(json.loads(line)["run_id"] == result.run_id for line in snapshot_lines)
    assert len(trace_lines) >= 10
