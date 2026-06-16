import tomllib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from deepresearch.cli import _index_corpus, app
from deepresearch.config import DeepResearchConfig

runner = CliRunner()


def test_help_lists_all_commands_without_mojibake():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "DeepResearch Agent" in result.output
    assert "index-corpus" in result.output
    assert "бк" not in result.output


def test_init_creates_valid_toml_and_refuses_overwrite(tmp_path):
    config_path = tmp_path / "config.toml"

    first = runner.invoke(app, ["init", "--output", str(config_path)])
    second = runner.invoke(app, ["init", "--output", str(config_path)])

    assert first.exit_code == 0
    assert config_path.exists()
    assert (
        tomllib.loads(config_path.read_text(encoding="utf-8"))["llm"]["provider"]
        == "mimo"
    )
    assert second.exit_code == 1


def test_mock_run_writes_four_artifacts(tmp_path):
    output = tmp_path / "custom-run"
    result = runner.invoke(
        app,
        ["run", "test question", "--mode", "mock", "--output", str(output)],
    )

    assert result.exit_code == 0, result.output
    assert {path.name for path in output.iterdir()} == {
        "report.md",
        "evaluation.json",
        "trace.jsonl",
        "memory_snapshot.jsonl",
    }


def test_real_run_fails_fast_when_required_credentials_are_missing(monkeypatch):
    monkeypatch.delenv("MIMO_API_KEY", raising=False)

    result = runner.invoke(app, ["run", "question", "--mode", "real"])

    assert result.exit_code != 0
    assert "MIMO_API_KEY" in result.output


def test_real_run_exits_nonzero_when_all_tasks_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "key")
    monkeypatch.setenv("TAVILY_API_KEY", "key")
    monkeypatch.setenv("DEEPRESEARCH_EMBEDDING_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEEPRESEARCH_EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("DEEPRESEARCH_RERANKER_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("DEEPRESEARCH_RERANKER_API_KEY", "key")

    output = tmp_path / "run"
    result_obj = SimpleNamespace(
        run_id="run-1",
        output_dir=output,
        evaluation=SimpleNamespace(task_success_rate=0),
    )

    with (
        patch("deepresearch.cli._build_runtime", return_value=(1, 2, 3, 4, 5)),
        patch(
            "deepresearch.core.run_manager.RunManager.run", new_callable=AsyncMock
        ) as run,
    ):
        run.return_value = result_obj
        result = runner.invoke(
            app,
            ["run", "question", "--mode", "real", "--output", str(output)],
        )

    assert result.exit_code == 2
    assert "no research tasks succeeded" in result.output


def test_index_corpus_invokes_real_indexing_workflow(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("content", encoding="utf-8")

    with patch(
        "deepresearch.cli._index_corpus",
        new_callable=AsyncMock,
        return_value=(1, 2),
    ) as index:
        result = runner.invoke(app, ["index-corpus", str(corpus)])

    assert result.exit_code == 0
    assert "Indexed 1 documents and 2 chunks" in result.output
    index.assert_called_once()


@pytest.mark.asyncio
async def test_index_corpus_chunks_embeds_and_upserts(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("local corpus content", encoding="utf-8")
    store = AsyncMock()

    with patch(
        "deepresearch.memory.milvus_store.MilvusStore",
        return_value=store,
    ) as store_cls:
        documents, chunks = await _index_corpus(
            corpus,
            DeepResearchConfig(),
            mode="mock",
        )

    assert documents == 1
    assert chunks == 1
    entries = store.upsert.await_args.args[0]
    assert entries[0].source_type == "chunk"
    assert entries[0].run_id == "corpus"
    assert len(entries[0].embedding) == 1024
    assert store_cls.call_args.kwargs["embedding_model"] == "Qwen3-Embedding-4B"


def test_eval_and_inspect_support_custom_output_root(tmp_path):
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "evaluation.json").write_text(
        '{"run_id": "run-1", "task_success_rate": 1.0}',
        encoding="utf-8",
    )
    (run_dir / "trace.jsonl").write_text('{"event_type":"x"}\n', encoding="utf-8")

    evaluation = runner.invoke(
        app,
        ["eval", "run-1", "--output-root", str(tmp_path / "runs")],
    )
    inspection = runner.invoke(
        app,
        ["inspect", "run-1", "--output-root", str(tmp_path / "runs")],
    )

    assert evaluation.exit_code == 0
    assert "task_success_rate: 1.0" in evaluation.output
    assert inspection.exit_code == 0
    assert "Trace events: 1" in inspection.output


def test_missing_paths_fail_cleanly():
    assert runner.invoke(app, ["index-corpus", "/nonexistent/path"]).exit_code == 1
    assert runner.invoke(app, ["eval", "missing"]).exit_code == 1
    assert runner.invoke(app, ["inspect", "missing"]).exit_code == 1


def test_config_accepts_explicit_file(tmp_path):
    config = tmp_path / "custom.toml"
    config.write_text('[llm]\nprovider = "deepseek"\n', encoding="utf-8")

    result = runner.invoke(app, ["config", "--config", str(config)])

    assert result.exit_code == 0
    assert "LLM provider: deepseek" in result.output


def test_inspect_timeline_shows_task_stats(tmp_path):
    run_dir = tmp_path / "runs" / "run-tl"
    run_dir.mkdir(parents=True)
    trace_lines = [
        '{"timestamp":"2026-06-16T00:00:00+00:00","event_type":"task_state_changed","task_id":"t1","metadata":{"status":"running"}}',
        '{"timestamp":"2026-06-16T00:00:01+00:00","event_type":"retriever_called","task_id":"t1","metadata":{"stage":"queries_generated","query_count":3}}',
        '{"timestamp":"2026-06-16T00:00:03+00:00","event_type":"retriever_called","task_id":"t1","metadata":{"stage":"retrieval_completed","document_count":10}}',
        '{"timestamp":"2026-06-16T00:00:04+00:00","event_type":"retriever_called","task_id":"t1","metadata":{"stage":"chunking_completed","chunk_count":25}}',
        '{"timestamp":"2026-06-16T00:00:06+00:00","event_type":"retriever_called","task_id":"t1","metadata":{"stage":"evidence_extraction_completed","evidence_count":4}}',
        '{"timestamp":"2026-06-16T00:00:07+00:00","event_type":"task_state_changed","task_id":"t1","metadata":{"status":"succeeded"}}',
    ]
    (run_dir / "trace.jsonl").write_text("\n".join(trace_lines), encoding="utf-8")

    result = runner.invoke(
        app,
        ["inspect", "run-tl", "--output-root", str(tmp_path / "runs"), "--timeline"],
    )

    assert result.exit_code == 0
    assert "t1" in result.output
    assert "succeeded" in result.output
    assert "3" in result.output
    assert "4" in result.output
    assert "7.000" in result.output
    assert "queries_generated=1.000s" in result.output
    assert "retrieval_completed=2.000s" in result.output


def test_inspect_timeline_no_trace(tmp_path):
    run_dir = tmp_path / "runs" / "run-empty"
    run_dir.mkdir(parents=True)

    result = runner.invoke(
        app,
        ["inspect", "run-empty", "--output-root", str(tmp_path / "runs"), "--timeline"],
    )

    assert result.exit_code == 0
    assert "No trace.jsonl" in result.output


def test_inspect_timeline_preserves_failure_reason(tmp_path):
    run_dir = tmp_path / "runs" / "run-failed"
    run_dir.mkdir(parents=True)
    trace_lines = [
        '{"timestamp":"2026-06-16T00:00:00+00:00","event_type":"task_state_changed","task_id":"t1","metadata":{"status":"running"}}',
        '{"timestamp":"2026-06-16T00:00:01+00:00","event_type":"task_state_changed","task_id":"t1","metadata":{"status":"error","error":"network unavailable"}}',
        '{"timestamp":"2026-06-16T00:00:02+00:00","event_type":"task_state_changed","task_id":"t1","metadata":{"status":"failed"}}',
    ]
    (run_dir / "trace.jsonl").write_text("\n".join(trace_lines), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "inspect",
            "run-failed",
            "--output-root",
            str(tmp_path / "runs"),
            "--timeline",
        ],
    )

    assert result.exit_code == 0
    assert "failed" in result.output
    assert "network unavailable" in result.output


def test_benchmark_uses_experiment_output_directory(tmp_path):
    dataset = tmp_path / "bench.jsonl"
    dataset.write_text(
        '{"id":"case-1","domain":"test","difficulty":"easy","question":"q","expected_facts":["f1","f2"],"required_citations":1,"tags":[]}\n',
        encoding="utf-8",
    )
    summary = {
        "total_cases": 1,
        "avg_task_success_rate": 1.0,
        "avg_citation_coverage": 0.5,
        "avg_elapsed_seconds": 0.1,
    }

    with (
        patch(
            "deepresearch.evaluation.benchmark.run_benchmark",
            new_callable=AsyncMock,
            return_value=([], summary),
        ) as run_benchmark,
        patch("deepresearch.cli._build_runtime", return_value=(1, 2, 3, 4, 5)),
    ):
        result = runner.invoke(
            app,
            [
                "benchmark",
                str(dataset),
                "--output",
                str(tmp_path / "outputs"),
                "--experiment",
                "exp-1",
            ],
        )

    assert result.exit_code == 0
    assert "experiment: exp-1" in result.output
    assert (
        run_benchmark.await_args.kwargs["output_dir"] == tmp_path / "outputs" / "exp-1"
    )


def test_benchmark_filters_case_id_and_limit(tmp_path):
    dataset = tmp_path / "bench.jsonl"
    dataset.write_text(
        "\n".join(
            [
                '{"id":"case-1","domain":"test","difficulty":"easy","question":"q1","expected_facts":[],"required_citations":0,"tags":[]}',
                '{"id":"case-2","domain":"test","difficulty":"easy","question":"q2","expected_facts":[],"required_citations":0,"tags":[]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "total_cases": 1,
        "avg_task_success_rate": 1.0,
        "avg_citation_coverage": 0.5,
        "avg_elapsed_seconds": 0.1,
    }

    with (
        patch(
            "deepresearch.evaluation.benchmark.run_benchmark",
            new_callable=AsyncMock,
            return_value=([], summary),
        ) as run_benchmark,
        patch("deepresearch.cli._build_runtime", return_value=(1, 2, 3, 4, 5)),
    ):
        result = runner.invoke(
            app,
            [
                "benchmark",
                str(dataset),
                "--case-id",
                "case-2",
                "--limit",
                "1",
            ],
        )

    assert result.exit_code == 0
    cases = run_benchmark.await_args.args[0]
    assert [case.id for case in cases] == ["case-2"]


def test_benchmark_passes_retriever_override(tmp_path):
    dataset = tmp_path / "bench.jsonl"
    dataset.write_text(
        '{"id":"case-1","domain":"test","difficulty":"easy","question":"q","expected_facts":[],"required_citations":0,"tags":[]}\n',
        encoding="utf-8",
    )
    summary = {
        "total_cases": 1,
        "avg_task_success_rate": 1.0,
        "avg_citation_coverage": 0.5,
        "avg_elapsed_seconds": 0.1,
    }

    with (
        patch(
            "deepresearch.evaluation.benchmark.run_benchmark",
            new_callable=AsyncMock,
            return_value=([], summary),
        ) as run_benchmark,
        patch("deepresearch.cli._build_runtime", return_value=(1, 2, 3, 4, 5)) as build,
    ):
        result = runner.invoke(
            app,
            ["benchmark", str(dataset), "--mode", "real", "--retriever", "mimo"],
        )
        assert result.exit_code == 0
        manager_factory = run_benchmark.await_args.args[1]
        manager_factory()

    assert build.call_args.kwargs["retriever_name"] == "mimo"


def test_benchmark_unknown_case_id_fails(tmp_path):
    dataset = tmp_path / "bench.jsonl"
    dataset.write_text(
        '{"id":"case-1","domain":"test","difficulty":"easy","question":"q","expected_facts":[],"required_citations":0,"tags":[]}\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["benchmark", str(dataset), "--case-id", "missing"],
    )

    assert result.exit_code == 1
    assert "Case not found: missing" in result.output


def test_benchmark_passes_corpus_to_build_runtime(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("local corpus content", encoding="utf-8")

    dataset = tmp_path / "bench.jsonl"
    dataset.write_text(
        '{"id":"case-1","domain":"test","difficulty":"easy","question":"q","expected_facts":[],"required_citations":0,"tags":[]}\n',
        encoding="utf-8",
    )
    summary = {
        "total_cases": 1,
        "avg_task_success_rate": 1.0,
        "avg_citation_coverage": 0.5,
        "avg_elapsed_seconds": 0.1,
    }

    with (
        patch(
            "deepresearch.evaluation.benchmark.run_benchmark",
            new_callable=AsyncMock,
            return_value=([], summary),
        ) as run_benchmark,
        patch("deepresearch.cli._build_runtime", return_value=(1, 2, 3, 4, 5)) as build,
    ):
        result = runner.invoke(
            app,
            [
                "benchmark",
                str(dataset),
                "--mode",
                "mock",
                "--retriever",
                "local",
                "--corpus",
                str(corpus),
            ],
        )
        assert result.exit_code == 0, result.output
        manager_factory = run_benchmark.await_args.args[1]
        manager_factory()

    assert build.call_args.kwargs["corpus"] == corpus


def test_run_prompt_provider_override_enables_langfuse(tmp_path):
    output = tmp_path / "run"
    manager_instance = SimpleNamespace(
        run=AsyncMock(
            return_value=SimpleNamespace(
                run_id="run-1",
                output_dir=output,
                evaluation=SimpleNamespace(task_success_rate=1),
            )
        )
    )

    with (
        patch("deepresearch.cli._build_runtime", return_value=(1, 2, 3, 4, 5)),
        patch(
            "deepresearch.core.run_manager.RunManager",
            return_value=manager_instance,
        ) as manager_cls,
    ):
        result = runner.invoke(
            app,
            [
                "run",
                "question",
                "--mode",
                "mock",
                "--output",
                str(output),
                "--prompt-provider",
                "langfuse_with_local_fallback",
            ],
        )

    assert result.exit_code == 0, result.output
    cfg = manager_cls.call_args.args[0]
    assert cfg.langfuse.enabled is True
    assert cfg.langfuse.prompt_provider == "langfuse_with_local_fallback"


def test_run_rejects_unknown_prompt_provider():
    result = runner.invoke(
        app,
        ["run", "question", "--prompt-provider", "unknown"],
    )

    assert result.exit_code != 0
    assert "prompt-provider" in result.output


def test_prompts_push_requires_langfuse_enabled(monkeypatch):
    """prompts push should fail if Langfuse is not enabled."""
    monkeypatch.setenv("DEEPRESEARCH_LANGFUSE_ENABLED", "false")
    result = runner.invoke(app, ["prompts", "push"])
    assert result.exit_code != 0
    assert "not enabled" in result.output.lower() or "langfuse" in result.output.lower()


def test_prompts_push_fails_when_client_unavailable(monkeypatch):
    monkeypatch.setenv("DEEPRESEARCH_LANGFUSE_ENABLED", "true")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    result = runner.invoke(app, ["prompts", "push"])

    assert result.exit_code != 0
    assert "client is unavailable" in result.output.lower()


def test_run_accepts_prompt_provider_option():
    """run command should accept --prompt-provider flag."""
    result = runner.invoke(app, ["run", "--help"])
    assert "prompt-provider" in result.output


def test_benchmark_accepts_prompt_provider_option():
    """benchmark command should accept --prompt-provider flag."""
    result = runner.invoke(app, ["benchmark", "--help"])
    assert "prompt-provider" in result.output
