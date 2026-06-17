import logging
from unittest.mock import MagicMock, patch

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
        adapter = LangfuseAdapter(
            enabled=True, public_key="pk", secret_key="sk"
        )
        cases = [
            {"id": "c1", "question": "Q1", "expected_facts": ["F1"], "domain": "d", "difficulty": "easy"},
            {"id": "c2", "question": "Q2", "expected_facts": ["F2"], "domain": "d", "difficulty": "hard"},
        ]
        count = adapter.push_dataset(dataset_name="test_ds", cases=cases)
        assert count == 2
        mock_client.create_dataset.assert_called_once_with(name="test_ds")
        assert mock_client.create_dataset_item.call_count == 2


def test_push_dataset_noop_when_disabled():
    """push_dataset should return 0 when adapter is disabled."""
    adapter = LangfuseAdapter(enabled=False)
    count = adapter.push_dataset(dataset_name="test", cases=[{"id": "c1"}])
    assert count == 0


def test_link_run_to_dataset():
    """link_run_to_dataset should call client.create_dataset_run_item."""
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_langfuse_cls.return_value = mock_client

    with patch.dict("sys.modules", {"langfuse": MagicMock(Langfuse=mock_langfuse_cls)}):
        adapter = LangfuseAdapter(enabled=True, public_key="pk", secret_key="sk")
        adapter.link_run_to_dataset(
            dataset_name="researchbench_full",
            case_id="rbf-001",
            run_id="run-1",
            trace_id="trace-1",
        )
        mock_client.create_dataset_run_item.assert_called_once()
        call_kwargs = mock_client.create_dataset_run_item.call_args.kwargs
        assert call_kwargs["dataset_name"] == "researchbench_full"
        assert call_kwargs["run_name"] == "run-1"


def test_link_run_to_dataset_noop_when_disabled():
    """link_run_to_dataset should be a no-op when adapter is disabled."""
    adapter = LangfuseAdapter(enabled=False)
    adapter.link_run_to_dataset(
        dataset_name="test", case_id="c1", run_id="r1", trace_id="t1",
    )
    # No error, no call
