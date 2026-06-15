import tomllib
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
    assert tomllib.loads(config_path.read_text(encoding="utf-8"))["llm"]["provider"] == "mimo"
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
        "deepresearch.memory.milvus_store.MilvusLiteStore",
        return_value=store,
    ):
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
