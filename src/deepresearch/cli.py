from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import tomli_w
import typer

from deepresearch.config import DeepResearchConfig, load_config

app = typer.Typer(
    name="deepresearch",
    help="DeepResearch Agent - multi-agent deep research system",
    no_args_is_help=True,
)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise typer.BadParameter(f"Required environment variable is missing: {name}")
    return value


def _required_config(value: str, name: str) -> str:
    if not value.strip():
        raise typer.BadParameter(f"Required configuration value is missing: {name}")
    return value


def _build_runtime(
    cfg: DeepResearchConfig,
    *,
    mode: str,
    retriever_name: str | None = None,
    corpus: Path | None = None,
) -> tuple[Any, Any, Any, Any, Any]:
    if mode == "mock":
        from deepresearch.embeddings.mock import MockEmbeddingClient
        from deepresearch.llm.mock import MockLLM
        from deepresearch.memory.store import MockMemoryStore
        from deepresearch.rerankers.mock import MockRerankerClient
        from deepresearch.retrieval.local_dataset import LocalDatasetRetriever
        from deepresearch.retrieval.mock import MockRetriever

        retriever = LocalDatasetRetriever(corpus) if corpus else MockRetriever()
        return (
            MockLLM(),
            retriever,
            MockMemoryStore(),
            MockEmbeddingClient(dim=cfg.embedding.dim),
            MockRerankerClient(),
        )

    if mode != "real":
        raise typer.BadParameter("--mode must be either 'mock' or 'real'")

    from deepresearch.embeddings.openai_compatible import (
        OpenAICompatibleEmbeddingClient,
    )
    from deepresearch.llm.deepseek import DeepSeekLLMClient
    from deepresearch.llm.mimo import MiMoLLMClient
    from deepresearch.memory.milvus_store import MilvusStore
    from deepresearch.rerankers.openai_compatible import (
        OpenAICompatibleRerankerClient,
    )
    from deepresearch.retrieval.local_dataset import LocalDatasetRetriever
    from deepresearch.retrieval.mimo_search import MiMoSearchRetriever
    from deepresearch.retrieval.tavily_search import TavilyWebSearchRetriever

    if cfg.llm.provider == "mimo":
        llm_api_key = _required_env(cfg.llm.api_key_env)
        llm = MiMoLLMClient(
            base_url=cfg.llm.base_url,
            api_key=llm_api_key,
            model=cfg.llm.model,
            default_temperature=cfg.llm.temperature,
            default_top_p=cfg.llm.top_p,
            default_max_completion_tokens=cfg.llm.max_completion_tokens,
            thinking=cfg.llm.thinking,
        )
    elif cfg.llm.provider == "deepseek":
        llm = DeepSeekLLMClient(
            base_url=cfg.llm.base_url,
            api_key=_required_env(cfg.llm.api_key_env),
            model=cfg.llm.model,
            default_temperature=cfg.llm.temperature,
            default_top_p=cfg.llm.top_p,
            default_max_completion_tokens=cfg.llm.max_completion_tokens,
        )
    else:
        raise typer.BadParameter(f"Unsupported LLM provider: {cfg.llm.provider}")

    selected_retriever = retriever_name or cfg.retrieval.search_provider
    if selected_retriever in {"tavily", "web_search"}:
        retriever = TavilyWebSearchRetriever(
            api_key=_required_env(cfg.web_search.api_key_env),
            timeout=cfg.web_search.timeout_seconds,
            max_retries=cfg.web_search.max_retries,
        )
    elif selected_retriever in {"mimo", "mimo_search"}:
        retriever = MiMoSearchRetriever(
            base_url=cfg.llm.base_url,
            api_key=_required_env(cfg.llm.api_key_env),
            model=cfg.llm.model,
            max_keyword=cfg.mimo_search.max_keyword,
            force_search=cfg.mimo_search.force_search,
            limit=cfg.mimo_search.limit,
        )
    elif selected_retriever in {"local", "local_dataset"}:
        if corpus is None or not corpus.is_dir():
            raise typer.BadParameter("--corpus is required for local retrieval")
        retriever = LocalDatasetRetriever(corpus)
    else:
        raise typer.BadParameter(f"Unsupported retriever: {selected_retriever}")

    embedding = OpenAICompatibleEmbeddingClient(
        base_url=_required_config(
            cfg.embedding.base_url,
            "embedding.base_url",
        ),
        api_key=_required_env(cfg.embedding.api_key_env),
        model=cfg.embedding.model,
        dim=cfg.embedding.dim,
        batch_size=cfg.embedding.batch_size,
        timeout=cfg.embedding.timeout_seconds,
        max_retries=cfg.embedding.max_retries,
        normalize=cfg.embedding.normalize,
        request_dimensions=cfg.embedding.request_dimensions,
    )
    reranker = OpenAICompatibleRerankerClient(
        base_url=_required_config(
            cfg.reranker.base_url,
            "reranker.base_url",
        ),
        api_key=_required_env(cfg.reranker.api_key_env),
        model=cfg.reranker.model,
        batch_size=cfg.reranker.batch_size,
        timeout=cfg.reranker.timeout_seconds,
        max_retries=cfg.reranker.max_retries,
    )
    memory = MilvusStore(
        uri=cfg.milvus.uri,
        chunks_collection=cfg.milvus.chunks_collection,
        memories_collection=cfg.milvus.memories_collection,
        dim=cfg.embedding.dim,
    )
    return llm, retriever, memory, embedding, reranker


@app.command()
def run(
    question: str = typer.Argument(help="Research question"),
    config_path: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
    mode: str = typer.Option("mock", help="Runtime mode: mock or real"),
    retriever: str | None = typer.Option(
        None, help="Retriever for real mode: tavily, mimo, or local"
    ),
    corpus: str | None = typer.Option(
        None, help="Local corpus directory for mock/local retrieval"
    ),
) -> None:
    """Run a deep research task."""
    from deepresearch.core.run_manager import RunManager

    cfg = load_config(config_path=config_path)
    corpus_path = Path(corpus) if corpus else None
    components = _build_runtime(
        cfg,
        mode=mode,
        retriever_name=retriever,
        corpus=corpus_path,
    )
    manager = RunManager(cfg, *components)
    result = asyncio.run(
        manager.run(question, output_dir=Path(output) if output else None)
    )
    if mode == "real" and result.evaluation.task_success_rate == 0:
        typer.echo(
            "Run failed: no research tasks succeeded. "
            f"See {result.output_dir / 'trace.jsonl'}",
            err=True,
        )
        raise typer.Exit(2)

    typer.echo(f"Run {result.run_id} complete.")
    typer.echo(f"Report: {result.output_dir / 'report.md'}")
    typer.echo(f"Memory: {result.output_dir / 'memory_snapshot.jsonl'}")
    typer.echo(f"Evaluation: {result.output_dir / 'evaluation.json'}")


@app.command(name="init")
def init_cmd(
    output: str = typer.Option("config.toml", "--output", "-o"),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing file"),
) -> None:
    """Create a default configuration file."""
    path = Path(output)
    if path.exists() and not force:
        typer.echo(f"Configuration already exists: {path}", err=True)
        raise typer.Exit(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        tomli_w.dumps(DeepResearchConfig().model_dump()),
        encoding="utf-8",
    )
    typer.echo(f"Created configuration: {path}")


async def _index_corpus(
    corpus: Path,
    cfg: DeepResearchConfig,
    *,
    mode: str,
) -> tuple[int, int]:
    from deepresearch.embeddings.mock import MockEmbeddingClient
    from deepresearch.embeddings.openai_compatible import (
        OpenAICompatibleEmbeddingClient,
    )
    from deepresearch.memory.milvus_store import MilvusStore
    from deepresearch.memory.store import MemoryEntry
    from deepresearch.retrieval.chunking import chunk_text
    from deepresearch.retrieval.local_dataset import LocalDatasetRetriever

    if mode not in {"mock", "real"}:
        raise typer.BadParameter("--mode must be either 'mock' or 'real'")
    embedding = (
        MockEmbeddingClient(dim=cfg.embedding.dim)
        if mode == "mock"
        else OpenAICompatibleEmbeddingClient(
            base_url=_required_config(
                cfg.embedding.base_url,
                "embedding.base_url",
            ),
            api_key=_required_env(cfg.embedding.api_key_env),
            model=cfg.embedding.model,
            dim=cfg.embedding.dim,
            batch_size=cfg.embedding.batch_size,
            timeout=cfg.embedding.timeout_seconds,
            max_retries=cfg.embedding.max_retries,
            normalize=cfg.embedding.normalize,
            request_dimensions=cfg.embedding.request_dimensions,
        )
    )
    documents = await LocalDatasetRetriever(corpus).retrieve([""], top_k=100000)
    chunks: list[tuple[Any, str]] = []
    for document in documents:
        for content in chunk_text(
            document.content,
            chunk_size=cfg.chunking.chunk_size_chars,
            overlap=cfg.chunking.chunk_overlap_chars,
            min_chunk=cfg.chunking.min_chunk_chars,
        ):
            chunks.append((document, content))

    vectors = (await embedding.embed([content for _, content in chunks])).embeddings
    entries = [
        MemoryEntry(
            id="corpus-" + hashlib.sha256(
                f"{document.id}:{content}".encode()
            ).hexdigest()[:24],
            run_id="corpus",
            task_id="",
            title=document.title,
            source_url=document.url or "",
            content=content,
            embedding=vector,
            source_type="chunk",
            confidence=1.0,
            metadata={"document_id": document.id, "source_type": document.source_type},
        )
        for (document, content), vector in zip(chunks, vectors, strict=True)
    ]
    store = MilvusStore(
        uri=cfg.milvus.uri,
        chunks_collection=cfg.milvus.chunks_collection,
        memories_collection=cfg.milvus.memories_collection,
        dim=cfg.embedding.dim,
    )
    await store.upsert(entries)
    return len(documents), len(entries)


@app.command(name="index-corpus")
def index_corpus(
    path: str = typer.Argument(help="Path to corpus directory"),
    config_path: str | None = typer.Option(None, "--config", "-c"),
    mode: str = typer.Option("mock", help="Embedding mode: mock or real"),
) -> None:
    """Chunk, embed, and index a local corpus into Milvus."""
    corpus = Path(path)
    if not corpus.is_dir():
        typer.echo(f"Error: {path} is not a directory", err=True)
        raise typer.Exit(1)
    documents, chunks = asyncio.run(
        _index_corpus(corpus, load_config(config_path=config_path), mode=mode)
    )
    typer.echo(f"Indexed {documents} documents and {chunks} chunks.")


def _run_dir(run_id: str, output_root: str) -> Path:
    return Path(output_root) / run_id


@app.command(name="eval")
def eval_cmd(
    run_id: str = typer.Argument(help="Run ID to evaluate"),
    output_root: str = typer.Option("outputs", help="Runs root directory"),
) -> None:
    """Display evaluation for a completed research run."""
    eval_path = _run_dir(run_id, output_root) / "evaluation.json"
    if not eval_path.exists():
        typer.echo(f"No evaluation found for run {run_id}", err=True)
        raise typer.Exit(1)
    data = json.loads(eval_path.read_text(encoding="utf-8"))
    typer.echo(f"Evaluation for run {run_id}:")
    for key, value in data.items():
        if key != "metadata":
            typer.echo(f"  {key}: {value}")


@app.command()
def inspect(
    run_id: str = typer.Argument(help="Run ID to inspect"),
    output_root: str = typer.Option("outputs", help="Runs root directory"),
) -> None:
    """Inspect trace and outputs of a research run."""
    run_dir = _run_dir(run_id, output_root)
    if not run_dir.is_dir():
        typer.echo(f"No outputs found for run {run_id}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Run directory: {run_dir}")
    for path in sorted(run_dir.iterdir()):
        typer.echo(f"  {path.name} ({path.stat().st_size} bytes)")
    trace_path = run_dir / "trace.jsonl"
    if trace_path.exists():
        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        typer.echo(f"\nTrace events: {len(lines)}")


@app.command(name="config")
def config_cmd(
    config_path: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Show current configuration."""
    cfg = load_config(config_path=config_path)
    typer.echo(f"LLM provider: {cfg.llm.provider}")
    typer.echo(f"LLM model: {cfg.llm.model}")
    typer.echo(f"Embedding model: {cfg.embedding.model}")
    typer.echo(f"Reranker model: {cfg.reranker.model}")
    typer.echo(f"Milvus URI: {cfg.milvus.uri}")
    typer.echo(f"Max concurrency: {cfg.executor.max_concurrency}")
