import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.config import DeepResearchConfig
from deepresearch.core.run_manager import RunManager
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.llm.mock import MockLLM
from deepresearch.memory.store import MockMemoryStore
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.lexical import configure_lexical_policy, get_lexical_policy
from deepresearch.retrieval.mock import MockRetriever
from deepresearch.schemas.task import ResearchPlan, TaskNode, TaskState


def _manager(memory: MockMemoryStore | None = None) -> RunManager:
    return RunManager(
        DeepResearchConfig(),
        MockLLM(),
        MockRetriever(),
        memory or MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
    )


def test_run_manager_accepts_injected_prompt_provider():
    provider = MagicMock()

    manager = RunManager(
        DeepResearchConfig(),
        MockLLM(),
        MockRetriever(),
        MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
        prompt_provider=provider,
    )

    assert manager._prompt_provider is provider


def test_run_manager_configures_lexical_policy():
    original = get_lexical_policy()
    config = DeepResearchConfig()
    config.lexical.tokenizer = "jieba"
    config.lexical.cjk_ngram_fallback = False

    try:
        RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        )

        policy = get_lexical_policy()
        assert policy.tokenizer == "jieba"
        assert policy.cjk_ngram_fallback is False
    finally:
        configure_lexical_policy(original)


def test_build_prompt_provider_fallback_constructs_local_provider(monkeypatch):
    config = DeepResearchConfig()
    config.langfuse.enabled = True
    config.langfuse.prompt_provider = "langfuse_with_local_fallback"
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    fake_client = MagicMock()

    with patch.dict(
        "sys.modules",
        {"langfuse": MagicMock(Langfuse=MagicMock(return_value=fake_client))},
    ):
        provider = RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        )._build_prompt_provider()

    assert provider is not None
    assert provider.get("planner")


def test_build_prompt_provider_strict_langfuse_raises_on_missing_prompt(monkeypatch):
    config = DeepResearchConfig()
    config.langfuse.enabled = True
    config.langfuse.prompt_provider = "langfuse"
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    fake_client = MagicMock()
    fake_client.get_prompt.side_effect = Exception("not found")

    with patch.dict(
        "sys.modules",
        {"langfuse": MagicMock(Langfuse=MagicMock(return_value=fake_client))},
    ):
        provider = RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        )._build_prompt_provider()

    assert provider is not None
    with pytest.raises(Exception, match="deepresearch/planner"):
        provider.get("planner")


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
async def test_run_manager_populates_langfuse_model_metadata(tmp_path):
    config = DeepResearchConfig()
    config.llm.provider = "mimo"
    config.langfuse.prompt_label = "staging"

    mock_adapter = MagicMock()
    mock_adapter.is_enabled = True
    mock_ctx = MagicMock()
    mock_ctx._parent_observation_id = "obs-run"

    def make_phase_cm():
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value={"_observation_id": "obs-phase"})
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    mock_ctx.create_phase.side_effect = lambda *a, **kw: make_phase_cm()
    mock_adapter.context.return_value = mock_ctx

    with patch(
        "deepresearch.core.run_manager.LangfuseAdapter", return_value=mock_adapter
    ):
        await RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        ).run("test question", output_dir=tmp_path / "run")

    # context() was called with metadata containing model_backend and prompt_label
    ctx_call_args = mock_adapter.context.call_args
    metadata = (
        ctx_call_args[0][2]
        if len(ctx_call_args.args) > 2
        else ctx_call_args.kwargs.get("metadata", {})
    )
    assert metadata.get("model_backend") == "mimo"
    assert metadata.get("prompt_label") == "staging"
    mock_adapter.report_run.assert_not_called()


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


@pytest.mark.asyncio
async def test_run_budget_populated(tmp_path):
    result = await _manager().run("test question", output_dir=tmp_path / "run")

    assert result.budget is not None
    assert result.budget.llm_calls >= 1
    assert result.budget.search_calls >= 1
    assert result.budget.chunks >= 1
    assert result.budget.embedding_batches >= 1
    assert result.budget.elapsed_seconds >= 0
    d = result.budget.to_dict()
    assert "llm_calls" in d
    assert "elapsed_seconds" in d
    evaluation = json.loads(
        (result.output_dir / "evaluation.json").read_text(encoding="utf-8")
    )
    assert evaluation["budget"] == d


@pytest.mark.asyncio
async def test_run_manager_replan_replaces_failed_task_and_resumes_downstream(tmp_path):
    config = DeepResearchConfig()
    config.executor.max_task_retries = 1
    config.executor.max_replans = 1
    initial_plan = ResearchPlan(
        plan_id="initial",
        question="test",
        tasks=[
            TaskNode(task_id="t1", description="primary research"),
            TaskNode(
                task_id="t2",
                description="dependent research",
                dependencies=["t1"],
            ),
        ],
    )
    replacement_plan = ResearchPlan(
        plan_id="replacement",
        question="test",
        tasks=[TaskNode(task_id="t1", description="alternate research")],
    )

    async def execute(task, *, run_id):
        if task.task_id == "t1":
            raise RuntimeError("primary source unavailable")
        return {
            "task_id": task.task_id,
            "queries": [],
            "evidence": [],
            "evidence_count": 1,
            "information_insufficient": False,
            "chunk_count": 0,
            "document_count": 0,
        }

    with (
        patch("deepresearch.core.run_manager.PlannerAgent") as planner_cls,
        patch("deepresearch.core.run_manager.ResearchAgent") as researcher_cls,
    ):
        planner_cls.return_value.plan = AsyncMock(return_value=initial_plan)
        planner_cls.return_value.replan = AsyncMock(return_value=replacement_plan)
        researcher_cls.return_value.execute = AsyncMock(side_effect=execute)
        result = await RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        ).run("test", output_dir=tmp_path / "run")

    tasks = {task.task_id: task for task in result.plan_tasks}
    assert tasks["t1"].status == TaskState.REPLANNING
    assert tasks["t2"].status == TaskState.REPLANNING
    assert tasks["replan-1-t1"].status == TaskState.SUCCEEDED
    assert tasks["replan-1-resume-t2"].status == TaskState.SUCCEEDED
    assert tasks["replan-1-resume-t2"].dependencies == ["replan-1-t1"]
    assert len(tasks) == len(result.plan_tasks)

    events = [
        json.loads(line)
        for line in (result.output_dir / "trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    completed = next(
        event for event in events if event["event_type"] == "replan_completed"
    )
    assert completed["run_id"] == result.run_id
    assert completed["metadata"]["new_task_ids"] == [
        "replan-1-t1",
        "replan-1-resume-t2",
    ]


@pytest.mark.asyncio
async def test_run_manager_creates_nested_langfuse_observations(tmp_path):
    """Verify RunManager creates Langfuse observations for each phase."""
    mock_langfuse_cls = MagicMock()
    mock_adapter = MagicMock()
    mock_langfuse_cls.return_value = mock_adapter
    mock_adapter.is_enabled = True

    mock_ctx = MagicMock()
    mock_ctx.trace_id = "trace-1"
    mock_ctx._parent_observation_id = "obs-run"

    # create_phase returns a context manager yielding a dict
    def make_phase_cm():
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value={"_observation_id": "obs-phase"})
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    mock_ctx.create_phase.side_effect = lambda *a, **kw: make_phase_cm()

    # create_task returns a context manager yielding a dict
    def make_task_cm():
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value={})
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    mock_ctx.create_task.side_effect = lambda *a, **kw: make_task_cm()

    mock_adapter.context.return_value = mock_ctx

    config = DeepResearchConfig()
    with patch("deepresearch.core.run_manager.LangfuseAdapter", mock_langfuse_cls):
        await RunManager(
            config,
            MockLLM(),
            MockRetriever(),
            MockMemoryStore(),
            MockEmbeddingClient(),
            MockRerankerClient(),
        ).run("test question", output_dir=tmp_path / "run")

    # context() was called
    mock_adapter.context.assert_called_once()

    # Verify phases were created
    phase_names = [c.args[0] for c in mock_ctx.create_phase.call_args_list]
    assert "plan" in phase_names
    assert "execute" in phase_names
    assert "synthesize" in phase_names
    assert "red-blue" in phase_names
    assert "evaluate" in phase_names

    # end_run was called with evaluation and budget
    mock_ctx.end_run.assert_called_once()
    end_kwargs = mock_ctx.end_run.call_args.kwargs
    assert "report" in end_kwargs
    assert "trace_summary" in end_kwargs
    mock_adapter.report_run.assert_not_called()
