import logging
from unittest.mock import MagicMock, patch

from deepresearch.evaluation.langfuse import LangfuseAdapter


def test_noop_when_disabled():
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
    assert mock_trace.score.call_count == 4
    assert mock_trace.update.call_args.kwargs["output"]["report"]["summary"] == "report"
    mock_client.flush.assert_called_once()
