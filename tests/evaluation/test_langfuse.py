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


def test_report_run_calls_langfuse():
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_trace = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    del mock_client.start_observation
    mock_client.trace.return_value = mock_trace

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

    mock_client.trace.assert_called_once()
    call_kwargs = mock_client.trace.call_args.kwargs
    assert "run-1" in call_kwargs["name"]
    assert call_kwargs["input"]["question"] == "test question"
    assert call_kwargs["metadata"]["trace_summary"]["event_count"] == 3
    assert mock_trace.score.call_count == 6
    assert mock_trace.update.call_args.kwargs["output"]["report"]["summary"] == "report"
    mock_client.flush.assert_called_once()


def test_report_run_calls_langfuse_judge_dimension_scores():
    """Langfuse v3 should send judge dimension scores and factual_hit_rate."""
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_trace = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    del mock_client.start_observation
    mock_client.trace.return_value = mock_trace

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
                "hallucination_flag": False,
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

    score_calls = mock_trace.score.call_args_list
    score_names = [c.kwargs.get("name") or (c.args[0] if c.args else None) for c in score_calls]
    assert "factual_hit_rate" in score_names
    assert "hallucination_flag" in score_names
    assert "judge_factuality" in score_names
    assert "judge_readability" in score_names
    assert "judge_citation_support" in score_names
    assert "judge_completeness" in score_names
    assert "judge_reasoning_consistency" in score_names
    # 4 original + 2 (factual_hit_rate, hallucination_flag) + 5 judge dims = 11
    assert len(score_calls) == 11


def test_report_run_calls_langfuse_v4_judge_dimension_scores():
    """Langfuse v4 should send judge dimension scores and factual_hit_rate."""
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
    # Check hallucination_flag sent as 1 (True -> int)
    hf_call = [c for c in score_calls if c.kwargs.get("name") == "hallucination_flag"][0]
    assert hf_call.kwargs["value"] == 1
    # 4 original + 2 (factual_hit_rate, hallucination_flag) + 5 judge dims = 11
    assert len(score_calls) == 11


def test_report_run_judge_scores_defaults_when_missing():
    """When evaluation has no judge_scores or factual_hit_rate, no extra scores sent."""
    mock_langfuse_cls = MagicMock()
    mock_client = MagicMock()
    mock_trace = MagicMock()
    mock_langfuse_cls.return_value = mock_client
    del mock_client.start_observation
    mock_client.trace.return_value = mock_trace

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

    score_calls = mock_trace.score.call_args_list
    score_names = [c.kwargs.get("name") or (c.args[0] if c.args else None) for c in score_calls]
    # Still sends factual_hit_rate (default 0) and hallucination_flag (default 0)
    assert "factual_hit_rate" in score_names
    assert "hallucination_flag" in score_names
    # No judge scores when judge_scores is empty/missing
    assert not any(n.startswith("judge_") for n in score_names)
    # 4 original + 2 = 6
    assert len(score_calls) == 6


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
    assert mock_client.create_score.call_count == 6
    mock_observation.end.assert_called_once()
    mock_client.flush.assert_called_once()
