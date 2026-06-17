import logging
from unittest.mock import MagicMock, patch

import pytest

from deepresearch.evaluation.langfuse import LangfuseAdapter


def test_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("DEEPRESEARCH_LANGFUSE_ENABLED", raising=False)
    adapter = LangfuseAdapter(enabled=False)
    assert not adapter.is_enabled
    adapter.report_run("r1", "q", {}, {}, {}, {}, {})


def test_noop_when_keys_missing(caplog, monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    with caplog.at_level(logging.WARNING):
        adapter = LangfuseAdapter(enabled=True, public_key="", secret_key="")
    assert not adapter.is_enabled
    assert "LANGFUSE_PUBLIC_KEY" in caplog.text


def test_report_run_calls_langfuse_v4():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_observation = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_client.start_observation.return_value = mock_observation

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(
            enabled=True, public_key="pk", secret_key="sk", host="http://test"
        )
        adapter.report_run(
            "run-1",
            "test question",
            {"summary": "report"},
            {
                "task_success_rate": 0.8,
                "citation_coverage": 0.9,
                "report_section_completeness": 1.0,
                "red_issue_count": 2,
            },
            {"llm_calls": 5},
            {"llm": "mimo"},
            {"event_count": 3},
        )

    mock_client.create_trace_id.assert_called_once_with(seed="run-1")
    mock_client.start_observation.assert_called_once()
    call_kwargs = mock_client.start_observation.call_args.kwargs
    assert call_kwargs["trace_context"]["trace_id"] == "trace-1"
    assert call_kwargs["input"]["question"] == "test question"
    assert call_kwargs["output"]["report"]["summary"] == "report"
    assert call_kwargs["metadata"]["trace_summary"]["event_count"] == 3
    assert mock_client.create_score.call_count == 6
    mock_observation.end.assert_called_once()
    mock_client.flush.assert_called_once()


def test_report_run_calls_langfuse_v4_judge_dimension_scores():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_observation = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_client.start_observation.return_value = mock_observation

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(
            enabled=True, public_key="pk", secret_key="sk", host="http://test"
        )
        adapter.report_run(
            "run-1",
            "test question",
            {"summary": "report"},
            {
                "task_success_rate": 0.8,
                "citation_coverage": 0.9,
                "report_section_completeness": 1.0,
                "red_issue_count": 2,
                "factual_hit_rate": 0.85,
                "hallucination_flag": True,
                "judge_scores": {
                    "factuality": 0.85,
                    "readability": 0.9,
                    "citation_support": 0.8,
                    "completeness": 0.7,
                    "reasoning_consistency": 0.75,
                },
            },
            {"llm_calls": 5},
            {"llm": "mimo"},
            {"event_count": 3},
        )

    score_calls = mock_client.create_score.call_args_list
    score_names = [c.kwargs.get("name") for c in score_calls]
    assert "factual_hit_rate" in score_names
    assert "hallucination_flag" in score_names
    assert "judge_factuality" in score_names
    assert "judge_readability" in score_names
    assert "judge_citation_support" in score_names
    assert "judge_completeness" in score_names
    assert "judge_reasoning_consistency" in score_names
    hf_call = next(
        c for c in score_calls if c.kwargs.get("name") == "hallucination_flag"
    )
    assert hf_call.kwargs["value"] == 1
    assert len(score_calls) == 11


def test_report_run_judge_scores_defaults_when_missing():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_observation = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_client.start_observation.return_value = mock_observation

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(
            enabled=True, public_key="pk", secret_key="sk", host="http://test"
        )
        adapter.report_run(
            "run-1",
            "test question",
            {"summary": "report"},
            {
                "task_success_rate": 0.8,
                "citation_coverage": 0.9,
                "report_section_completeness": 1.0,
                "red_issue_count": 2,
            },
            {"llm_calls": 5},
            {"llm": "mimo"},
            {"event_count": 3},
        )

    score_names = [
        c.kwargs.get("name") for c in mock_client.create_score.call_args_list
    ]
    assert "factual_hit_rate" in score_names
    assert "hallucination_flag" in score_names
    assert not any(n.startswith("judge_") for n in score_names)
    assert len(score_names) == 6


def test_langfuse_trace_metadata_includes_benchmark_fields():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_observation = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_client.start_observation.return_value = mock_observation

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(
            enabled=True, public_key="pk", secret_key="sk", host="http://test"
        )
        adapter.report_run(
            "r1",
            "Q",
            {"summary": "R"},
            {
                "task_success_rate": 0.8,
                "citation_coverage": 0.7,
                "report_section_completeness": 1.0,
                "red_issue_count": 0,
                "factual_hit_rate": 0.9,
                "hallucination_flag": False,
            },
            {},
            {"model": "test"},
            {},
            case_id="rbf-001",
            domain="llm_agents",
            difficulty="medium",
            question_lang="zh",
            evidence_lang="mixed",
            source_dataset="researchbench_full",
            model_backend="mimo",
            prompt_label="production",
        )

    metadata = mock_client.start_observation.call_args.kwargs.get("metadata", {})
    assert metadata.get("case_id") == "rbf-001"
    assert metadata.get("domain") == "llm_agents"
    assert metadata.get("difficulty") == "medium"
    assert metadata.get("question_lang") == "zh"
    assert metadata.get("evidence_lang") == "mixed"
    assert metadata.get("source_dataset") == "researchbench_full"
    assert metadata.get("model_backend") == "mimo"
    assert metadata.get("prompt_label") == "production"


def test_push_dataset_creates_langfuse_dataset():
    """push_dataset should call client.create_dataset and client.create_dataset_item."""
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        cases = [
            {
                "id": "c1",
                "question": "Q1",
                "expected_facts": ["F1"],
                "domain": "d",
                "difficulty": "easy",
            },
            {
                "id": "c2",
                "question": "Q2",
                "expected_facts": ["F2"],
                "domain": "d",
                "difficulty": "hard",
            },
        ]
        count = adapter.push_dataset(dataset_name="test_ds", cases=cases)
        assert count == 2
        mock_client.create_dataset.assert_called_once_with(name="test_ds")
        assert mock_client.create_dataset_item.call_count == 2
        first_item = mock_client.create_dataset_item.call_args_list[0].kwargs
        assert first_item["id"] == "c1"
        assert first_item["input"]["case_id"] == "c1"


def test_push_dataset_noop_when_disabled():
    """push_dataset should return 0 when adapter is disabled."""
    adapter = LangfuseAdapter(enabled=False)
    count = adapter.push_dataset(dataset_name="test", cases=[{"id": "c1"}])
    assert count == 0


def test_report_benchmark_scores_uses_prefixed_scores():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        adapter.report_benchmark_scores(
            trace_id="trace-1",
            evaluation={
                "task_success_rate": 1.0,
                "citation_coverage": 0.75,
                "report_section_completeness": 1.0,
                "factual_hit_rate": 0.8,
                "hallucination_flag": False,
                "judge_scores": {"factuality": 0.9},
            },
        )

    score_names = [
        c.kwargs.get("name") for c in mock_client.create_score.call_args_list
    ]
    assert "benchmark_task_success_rate" in score_names
    assert "benchmark_factual_hit_rate" in score_names
    assert "benchmark_judge_factuality" in score_names
    mock_client.flush.assert_called_once()


def test_link_run_to_dataset_logs_current_sdk_metadata(caplog):
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        with caplog.at_level(logging.INFO):
            adapter.link_run_to_dataset(
                dataset_name="researchbench_full",
                case_id="rbf-001",
                run_id="run-1",
                trace_id="trace-1",
            )

    assert "researchbench_full" in caplog.text
    assert "rbf-001" in caplog.text
    assert not mock_client.method_calls


def test_link_run_to_dataset_noop_when_disabled():
    """link_run_to_dataset should be a no-op when adapter is disabled."""
    adapter = LangfuseAdapter(enabled=False)
    adapter.link_run_to_dataset(
        dataset_name="test",
        case_id="c1",
        run_id="r1",
        trace_id="t1",
    )


def test_langfuse_context_create_phase_creates_nested_span():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_run_obs = MagicMock()
    mock_run_obs.observation_id = "obs-run"
    mock_phase_obs = MagicMock()
    mock_phase_obs.observation_id = "obs-phase"

    call_count = 0

    def start_obs_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_run_obs
        return mock_phase_obs

    mock_client.start_observation.side_effect = start_obs_side_effect

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        with adapter.context("run-1", "test question", {"llm": "mimo"}) as ctx:  # noqa: SIM117
            with ctx.create_phase("plan", {"question": "test question"}):
                pass

    # First call: run-level agent observation
    first_call = mock_client.start_observation.call_args_list[0]
    assert first_call.kwargs["as_type"] == "agent"
    assert first_call.kwargs["name"] == "deepresearch-run-1"

    # Second call: phase-level span nested under run
    phase_call = mock_client.start_observation.call_args_list[1]
    assert phase_call.kwargs["name"] == "plan"
    assert phase_call.kwargs["trace_context"]["trace_id"] == "trace-1"
    assert phase_call.kwargs["parent_observation_id"] == "obs-run"
    assert phase_call.kwargs["as_type"] == "span"

    mock_phase_obs.end.assert_called_once()


def test_langfuse_context_create_phase_ends_on_exception():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_run_obs = MagicMock()
    mock_run_obs.observation_id = "obs-run"
    mock_phase_obs = MagicMock()
    mock_phase_obs.observation_id = "obs-phase"

    call_count = 0

    def start_obs_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        return mock_run_obs if call_count == 1 else mock_phase_obs

    mock_client.start_observation.side_effect = start_obs_side_effect

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        with adapter.context("run-1", "q", {}) as ctx:  # noqa: SIM117
            with pytest.raises(ValueError, match="boom"):
                with ctx.create_phase("plan", {"q": "q"}):
                    raise ValueError("boom")

    mock_phase_obs.end.assert_called_once()


def test_langfuse_context_create_task_nests_under_phase():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_run_obs = MagicMock()
    mock_run_obs.observation_id = "obs-run"
    mock_phase_obs = MagicMock()
    mock_phase_obs.observation_id = "obs-phase"
    mock_task_obs = MagicMock()
    mock_task_obs.observation_id = "obs-task"

    call_count = 0

    def start_obs_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_run_obs
        if call_count == 2:
            return mock_phase_obs
        return mock_task_obs

    mock_client.start_observation.side_effect = start_obs_side_effect

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        with adapter.context("run-1", "q", {}) as ctx:  # noqa: SIM117
            with ctx.create_phase("execute", {"tasks": 2}) as phase:
                phase_id = phase["_observation_id"]
                with ctx.create_task("t1", "research task", phase_id):
                    pass

    task_call = mock_client.start_observation.call_args_list[2]
    assert task_call.kwargs["name"] == "task-t1"
    assert task_call.kwargs["parent_observation_id"] == "obs-phase"
    assert task_call.kwargs["as_type"] == "span"
    mock_task_obs.end.assert_called_once()


def test_langfuse_context_end_run_emits_evaluation_and_budget_scores():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_run_obs = MagicMock()
    mock_run_obs.observation_id = "obs-run"
    mock_client.start_observation.return_value = mock_run_obs

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        ctx = adapter.context("run-1", "q", {})
        assert ctx is not None
        ctx.end_run(
            {
                "task_success_rate": 1.0,
                "citation_coverage": 0.8,
                "report_section_completeness": 1.0,
                "factual_hit_rate": 0.9,
                "hallucination_flag": False,
                "red_issue_count": 2,
                "judge_scores": {"factuality": 0.85},
            },
            {
                "llm_calls": 5,
                "search_calls": 3,
                "fetched_docs": 10,
                "chunks": 40,
                "embedding_batches": 2,
                "rerank_calls": 1,
                "prompt_tokens": 5000,
                "completion_tokens": 1000,
                "total_tokens": 6000,
                "elapsed_seconds": 12.345,
            },
            report={"summary": "report"},
            trace_summary={"event_count": 3},
        )

    score_calls = mock_client.create_score.call_args_list
    score_names = [c.kwargs["name"] for c in score_calls]

    # Evaluation scores
    assert "task_success_rate" in score_names
    assert "citation_coverage" in score_names
    assert "factual_hit_rate" in score_names
    assert "hallucination_flag" in score_names
    assert "judge_factuality" in score_names

    # Budget scores
    assert "budget_llm_calls" in score_names
    assert "budget_search_calls" in score_names
    assert "budget_total_tokens" in score_names
    assert "budget_elapsed_seconds" in score_names

    # All scores use the same trace_id
    assert all(c.kwargs["trace_id"] == "trace-1" for c in score_calls)

    # Run observation was ended
    mock_run_obs.update.assert_called_once()
    update_kwargs = mock_run_obs.update.call_args.kwargs
    assert update_kwargs["output"]["report"]["summary"] == "report"
    assert update_kwargs["output"]["budget"]["llm_calls"] == 5
    assert update_kwargs["metadata"]["trace_summary"]["event_count"] == 3
    mock_run_obs.end.assert_called_once()
    mock_client.flush.assert_called_once()


def test_langfuse_context_exit_closes_run_on_exception():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    mock_client.create_trace_id.return_value = "trace-1"
    mock_run_obs = MagicMock()
    mock_run_obs.observation_id = "obs-run"
    mock_client.start_observation.return_value = mock_run_obs

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        with (
            pytest.raises(RuntimeError, match="boom"),
            adapter.context("run-1", "q", {}),
        ):
            raise RuntimeError("boom")

    mock_run_obs.update.assert_called_once()
    assert mock_run_obs.update.call_args.kwargs["level"] == "ERROR"
    mock_run_obs.end.assert_called_once()


def test_langfuse_context_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("DEEPRESEARCH_LANGFUSE_ENABLED", raising=False)
    adapter = LangfuseAdapter(enabled=False)
    assert adapter.context("run-1", "q", {}) is None
