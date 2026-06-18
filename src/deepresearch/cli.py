from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
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


def _load_config_or_exit(config_path: str | None = None) -> DeepResearchConfig:
    try:
        return load_config(config_path=config_path)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


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

    from deepresearch.memory.milvus_store import MilvusStore
    from deepresearch.models import (
        build_embedding_client,
        build_llm_client,
        build_reranker_client,
    )
    from deepresearch.retrieval.local_dataset import LocalDatasetRetriever
    from deepresearch.retrieval.mimo_search import MiMoSearchRetriever
    from deepresearch.retrieval.tavily_search import TavilyWebSearchRetriever

    try:
        llm = build_llm_client(cfg)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

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

    try:
        embedding = build_embedding_client(cfg)
        reranker = build_reranker_client(cfg)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    memory = MilvusStore(
        uri=cfg.milvus.uri,
        chunks_collection=cfg.milvus.chunks_collection,
        memories_collection=cfg.milvus.memories_collection,
        dim=cfg.embedding.dim,
        embedding_model=cfg.embedding.model,
    )
    return llm, retriever, memory, embedding, reranker


def _apply_prompt_provider_override(
    cfg: DeepResearchConfig, prompt_provider: str | None
) -> None:
    if not prompt_provider:
        return
    allowed = {"local", "langfuse", "langfuse_with_local_fallback"}
    if prompt_provider not in allowed:
        raise typer.BadParameter(
            "--prompt-provider must be one of: "
            "local, langfuse, langfuse_with_local_fallback"
        )
    cfg.langfuse.prompt_provider = prompt_provider
    if prompt_provider != "local":
        cfg.langfuse.enabled = True


def _apply_benchmark_model_metadata(cases: list[Any], cfg: DeepResearchConfig) -> None:
    for case in cases:
        if not getattr(case, "model_backend", ""):
            case.model_backend = cfg.llm.provider
        if not getattr(case, "model_name", ""):
            case.model_name = cfg.llm.model


def _raise_runtime_http_error(exc: httpx.HTTPStatusError) -> None:
    status = exc.response.status_code
    reason = exc.response.reason_phrase
    url = exc.request.url
    if status == 429:
        typer.echo(
            "Run failed: provider rate limit exceeded "
            f"(HTTP 429 Too Many Requests) for {url}.",
            err=True,
        )
        typer.echo(
            "Retry later, or lower concurrency/LLM calls with a small real-run config. "
            "For a cheap smoke run, use: --config examples/configs/benchmark_smoke.toml",
            err=True,
        )
    else:
        body = exc.response.text.strip()
        if len(body) > 500:
            body = body[:500] + "..."
        typer.echo(
            f"Run failed: provider returned HTTP {status} {reason} for {url}.",
            err=True,
        )
        if body:
            typer.echo(f"Response body: {body}", err=True)
    raise typer.Exit(1) from exc


def _raise_runtime_request_error(exc: httpx.RequestError) -> None:
    typer.echo(
        f"Run failed: network request error for {exc.request.url}: {exc}", err=True
    )
    raise typer.Exit(1) from exc


@app.command()
def run(
    question: str = typer.Argument(help="Research question"),
    config_path: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
    mode: str = typer.Option("real", help="Runtime mode: real or mock"),
    retriever: str | None = typer.Option(
        None, help="Retriever for real mode: tavily, mimo, or local"
    ),
    corpus: str | None = typer.Option(
        None, help="Local corpus directory for mock/local retrieval"
    ),
    prompt_provider: str | None = typer.Option(
        None,
        "--prompt-provider",
        help="Prompt source: local, langfuse, langfuse_with_local_fallback",
    ),
    llm_provider: str | None = typer.Option(
        None, "--llm-provider", help="LLM provider: mimo, deepseek, openai_compatible"
    ),
    llm_model: str | None = typer.Option(
        None, "--llm-model", help="Override LLM model name"
    ),
    max_concurrency: int | None = typer.Option(
        None, "--max-concurrency", help="Override DAG task concurrency for this run"
    ),
    retrieval_concurrency: int | None = typer.Option(
        None,
        "--retrieval-concurrency",
        help="Override per-task retriever request concurrency for this run",
    ),
) -> None:
    """Run a deep research task."""
    from deepresearch.core.run_manager import RunManager

    cfg = _load_config_or_exit(config_path=config_path)
    if llm_provider:
        cfg.llm.provider = llm_provider
    if llm_model:
        cfg.llm.model = llm_model
    if max_concurrency is not None:
        if max_concurrency < 1:
            raise typer.BadParameter("--max-concurrency must be >= 1")
        cfg.executor.max_concurrency = max_concurrency
    if retrieval_concurrency is not None:
        if retrieval_concurrency < 1:
            raise typer.BadParameter("--retrieval-concurrency must be >= 1")
        cfg.retrieval.request_concurrency = retrieval_concurrency
    _apply_prompt_provider_override(cfg, prompt_provider)
    corpus_path = Path(corpus) if corpus else None
    components = _build_runtime(
        cfg,
        mode=mode,
        retriever_name=retriever,
        corpus=corpus_path,
    )
    manager = RunManager(cfg, *components)
    try:
        result = asyncio.run(
            manager.run(question, output_dir=Path(output) if output else None)
        )
    except httpx.HTTPStatusError as exc:
        _raise_runtime_http_error(exc)
    except httpx.RequestError as exc:
        _raise_runtime_request_error(exc)
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
    from deepresearch.memory.milvus_store import MilvusStore
    from deepresearch.memory.store import MemoryEntry
    from deepresearch.models import build_embedding_client
    from deepresearch.retrieval.chunking import chunk_text
    from deepresearch.retrieval.local_dataset import LocalDatasetRetriever

    if mode not in {"mock", "real"}:
        raise typer.BadParameter("--mode must be either 'mock' or 'real'")
    if mode == "mock":
        embedding = MockEmbeddingClient(dim=cfg.embedding.dim)
    else:
        try:
            embedding = build_embedding_client(cfg)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
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
            id="corpus-"
            + hashlib.sha256(f"{document.id}:{content}".encode()).hexdigest()[:24],
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
        embedding_model=cfg.embedding.model,
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
        _index_corpus(corpus, _load_config_or_exit(config_path=config_path), mode=mode)
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
    timeline: bool = typer.Option(
        False, "--timeline", "-t", help="Show per-task timeline"
    ),
) -> None:
    """Inspect trace and outputs of a research run."""
    run_dir = _run_dir(run_id, output_root)
    if not run_dir.is_dir():
        typer.echo(f"No outputs found for run {run_id}", err=True)
        raise typer.Exit(1)
    if timeline:
        _print_timeline(run_dir)
        return
    typer.echo(f"Run directory: {run_dir}")
    for path in sorted(run_dir.iterdir()):
        typer.echo(f"  {path.name} ({path.stat().st_size} bytes)")
    trace_path = run_dir / "trace.jsonl"
    if trace_path.exists():
        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        typer.echo(f"\nTrace events: {len(lines)}")


def _print_timeline(run_dir: Path) -> None:
    trace_path = run_dir / "trace.jsonl"
    if not trace_path.exists():
        typer.echo("No trace.jsonl found.")
        return
    task_stats = _parse_timeline(trace_path)
    if not task_stats:
        typer.echo("No task events found in trace.")
        return
    header = (
        f"{'task_id':<22} {'status':<12} {'elapsed':<9} {'queries':<8} "
        f"{'docs':<6} {'chunks':<7} {'evidence':<9} error"
    )
    typer.echo(header)
    typer.echo("-" * len(header))
    for stats in task_stats:
        typer.echo(
            f"{stats['task_id']:<22} "
            f"{stats['status']:<12} "
            f"{stats.get('elapsed_seconds', 0.0):<9.3f} "
            f"{stats.get('query_count', 0):<8} "
            f"{stats.get('document_count', 0):<6} "
            f"{stats.get('chunk_count', 0):<7} "
            f"{stats.get('evidence_count', 0):<9} "
            f"{stats.get('error', '')}"
        )
        stage_durations = stats.get("stage_durations", {})
        if stage_durations:
            details = ", ".join(
                f"{stage}={seconds:.3f}s" for stage, seconds in stage_durations.items()
            )
            typer.echo(f"  stages: {details}")


def _parse_timeline(trace_path: Path) -> list[dict]:
    task_stats: dict[str, dict] = {}
    for line in trace_path.read_text(encoding="utf-8").strip().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        task_id = event.get("task_id", "")
        if not task_id:
            continue
        timestamp = _parse_trace_timestamp(event.get("timestamp"))
        stats = task_stats.setdefault(
            task_id,
            {
                "task_id": task_id,
                "status": "unknown",
                "stage_durations": {},
                "_first_timestamp": timestamp,
                "_last_timestamp": timestamp,
                "_previous_timestamp": timestamp,
            },
        )
        if timestamp is not None:
            if stats["_first_timestamp"] is None:
                stats["_first_timestamp"] = timestamp
            stats["_last_timestamp"] = timestamp
        event_type = event.get("event_type", "")
        metadata = event.get("metadata", {})
        if event_type == "retriever_called":
            stage = metadata.get("stage", "")
            previous = stats.get("_previous_timestamp")
            if timestamp is not None and previous is not None and stage:
                stats["stage_durations"][stage] = max(
                    0.0, (timestamp - previous).total_seconds()
                )
            if stage == "queries_generated":
                stats["query_count"] = metadata.get("query_count", 0)
            elif stage == "retrieval_completed":
                stats["document_count"] = metadata.get("document_count", 0)
            elif stage == "chunking_completed":
                stats["chunk_count"] = metadata.get("chunk_count", 0)
            elif stage == "evidence_extraction_completed":
                stats["evidence_count"] = metadata.get("evidence_count", 0)
        elif event_type == "task_state_changed":
            status = metadata.get("status", "")
            if status:
                stats["status"] = status
            if metadata.get("error"):
                stats["error"] = metadata["error"]
        if timestamp is not None:
            stats["_previous_timestamp"] = timestamp

    results = []
    for stats in task_stats.values():
        first = stats.pop("_first_timestamp")
        last = stats.pop("_last_timestamp")
        stats.pop("_previous_timestamp")
        stats["elapsed_seconds"] = (
            max(0.0, (last - first).total_seconds())
            if first is not None and last is not None
            else 0.0
        )
        results.append(stats)
    return results


def _parse_trace_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@app.command(name="config")
def config_cmd(
    config_path: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Show current configuration."""
    cfg = _load_config_or_exit(config_path=config_path)
    typer.echo(f"LLM provider: {cfg.llm.provider}")
    typer.echo(f"LLM model: {cfg.llm.model}")
    typer.echo(f"Embedding model: {cfg.embedding.model}")
    typer.echo(f"Reranker model: {cfg.reranker.model}")
    typer.echo(f"Milvus URI: {cfg.milvus.uri}")
    typer.echo(f"Max concurrency: {cfg.executor.max_concurrency}")


@app.command()
def doctor(
    config_path: str | None = typer.Option(None, "--config", "-c"),
    real: bool = typer.Option(
        False,
        "--real",
        help="Run real endpoint and Milvus checks instead of offline config checks only.",
    ),
) -> None:
    """Check environment and dependencies for real-mode readiness."""
    from deepresearch.doctor import run_doctor

    cfg = _load_config_or_exit(config_path=config_path)
    report = run_doctor(cfg, real=real)

    for check in report.checks:
        icon = "OK" if check.ok else "FAIL"
        prefix = f"[{icon}]"
        typer.echo(f"{prefix} {check.message}")

    if not report.all_ok:
        typer.echo(f"\n{len(report.errors)} check(s) failed.")
        raise typer.Exit(1)
    typer.echo("\nAll checks passed.")


@app.command(name="prompts")
def prompts_cmd(
    action: str = typer.Argument(help="Action: push"),
    label: str = typer.Option("staging", "--label", "-l", help="Langfuse prompt label"),
    config_path: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Manage prompts (push to Langfuse)."""
    if action != "push":
        typer.echo(f"Unknown action: {action}. Use 'push'.", err=True)
        raise typer.Exit(1)

    cfg = _load_config_or_exit(config_path=config_path)
    if not cfg.langfuse.enabled:
        typer.echo(
            "Langfuse is not enabled. Set DEEPRESEARCH_LANGFUSE_ENABLED=1.", err=True
        )
        raise typer.Exit(1)

    from deepresearch.prompts.provider import LocalPromptProvider

    prompts_dir = Path(__file__).resolve().parent / "prompts"
    local = LocalPromptProvider(prompts_dir)
    names = local.list_names()

    from deepresearch.evaluation.langfuse import LangfuseAdapter

    adapter = LangfuseAdapter(
        enabled=True,
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
        host=cfg.langfuse.host,
    )
    client = adapter._client
    if client is None:
        typer.echo(
            "Langfuse client is unavailable. Check LANGFUSE_PUBLIC_KEY, "
            "LANGFUSE_SECRET_KEY, LANGFUSE_HOST, and the langfuse package.",
            err=True,
        )
        raise typer.Exit(1)

    succeeded = 0
    failed = 0
    for name in names:
        content = local.get(name)
        prompt_name = f"deepresearch/{name}"
        try:
            client.create_prompt(
                name=prompt_name,
                prompt=content,
                labels=[label],
                type="text",
                config={"source": "local bootstrap"},
            )
            typer.echo(f"  pushed: {prompt_name} (label={label})")
            succeeded += 1
        except Exception as exc:
            typer.echo(f"  failed: {prompt_name} - {exc}", err=True)
            failed += 1

    typer.echo(f"\nPushed {succeeded}/{len(names)} prompts with label '{label}'.")
    if failed:
        raise typer.Exit(1)


@app.command(name="datasets")
def datasets_cmd(
    action: str = typer.Argument(help="Action: push"),
    dataset: str = typer.Option(
        "researchbench_smoke5", "--dataset", "-d", help="Dataset name in Langfuse"
    ),
    source: str = typer.Option(
        "examples/bench", "--source", "-s", help="Local JSONL directory"
    ),
    config_path: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Manage Langfuse datasets (push local JSONL to Langfuse)."""
    if action != "push":
        typer.echo(f"Unknown action: {action}. Use 'push'.", err=True)
        raise typer.Exit(1)

    cfg = _load_config_or_exit(config_path=config_path)
    if not cfg.langfuse.enabled:
        typer.echo(
            "Langfuse is not enabled. Set DEEPRESEARCH_LANGFUSE_ENABLED=1.", err=True
        )
        raise typer.Exit(1)

    from deepresearch.evaluation.langfuse import LangfuseAdapter

    adapter = LangfuseAdapter(
        enabled=True,
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
        host=cfg.langfuse.host,
    )
    if not adapter.is_enabled:
        typer.echo("Langfuse adapter failed to initialize.", err=True)
        raise typer.Exit(1)

    # Find the JSONL file
    source_path = Path(source)
    jsonl_path = source_path / f"{dataset}.jsonl"
    if not jsonl_path.is_file():
        # Try direct path
        jsonl_path = Path(dataset) if Path(dataset).is_file() else jsonl_path
    if not jsonl_path.is_file():
        typer.echo(f"Dataset file not found: {jsonl_path}", err=True)
        raise typer.Exit(1)

    # Load raw cases
    cases = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))

    typer.echo(f"Pushing {len(cases)} cases to Langfuse dataset '{dataset}'...")
    count = adapter.push_dataset(dataset_name=dataset, cases=cases)
    typer.echo(f"Pushed {count}/{len(cases)} items.")


@app.command(name="benchmark")
def benchmark_cmd(
    dataset: str = typer.Argument(help="Path to benchmark JSONL dataset"),
    config_path: str | None = typer.Option(None, "--config", "-c"),
    output: str = typer.Option("outputs/bench", "--output", "-o"),
    experiment: str = typer.Option("", "--experiment", "-e"),
    mode: str = typer.Option("mock", "--mode", "-m"),
    retriever: str | None = typer.Option(
        None, "--retriever", help="Retriever for real mode: tavily, mimo, or local"
    ),
    corpus: str | None = typer.Option(
        None, "--corpus", help="Local corpus directory for local retrieval"
    ),
    case_id: str | None = typer.Option(
        None, "--case-id", help="Run only one benchmark case by ID"
    ),
    limit: int | None = typer.Option(
        None, "--limit", help="Run only the first N benchmark cases after filtering"
    ),
    prompt_provider: str | None = typer.Option(
        None,
        "--prompt-provider",
        help="Prompt source: local, langfuse, langfuse_with_local_fallback",
    ),
    max_concurrency: int | None = typer.Option(
        None,
        "--max-concurrency",
        help="Max concurrent benchmark cases (default: 1 = serial)",
    ),
    llm_provider: str | None = typer.Option(
        None, "--llm-provider", help="LLM provider: mimo, deepseek, openai_compatible"
    ),
    llm_model: str | None = typer.Option(
        None, "--llm-model", help="Override LLM model name"
    ),
) -> None:
    """Run benchmark suite and produce results.jsonl + summary.json."""
    from deepresearch.core.run_manager import RunManager
    from deepresearch.evaluation.benchmark import load_dataset, run_benchmark

    dataset_path = Path(dataset)
    if not dataset_path.is_file():
        typer.echo(f"Dataset not found: {dataset}", err=True)
        raise typer.Exit(1)

    cases = load_dataset(dataset_path)
    if case_id:
        cases = [case for case in cases if case.id == case_id]
        if not cases:
            typer.echo(f"Case not found: {case_id}", err=True)
            raise typer.Exit(1)
    if limit is not None:
        if limit < 1:
            raise typer.BadParameter("--limit must be >= 1")
        cases = cases[:limit]
    typer.echo(f"Loaded {len(cases)} benchmark cases from {dataset}")

    cfg = _load_config_or_exit(config_path=config_path)
    if llm_provider:
        cfg.llm.provider = llm_provider
    if llm_model:
        cfg.llm.model = llm_model
    _apply_prompt_provider_override(cfg, prompt_provider)
    _apply_benchmark_model_metadata(cases, cfg)
    if max_concurrency is not None:
        if max_concurrency < 1:
            raise typer.BadParameter("--max-concurrency must be >= 1")
        cfg.benchmark.max_concurrency = max_concurrency
    experiment_id = (
        experiment or f"{dataset_path.stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    output_dir = Path(output) / experiment_id
    cfg.langfuse.experiment_name = experiment_id

    def make_manager() -> RunManager:
        corpus_path = Path(corpus) if corpus else None
        components = _build_runtime(
            cfg, mode=mode, retriever_name=retriever, corpus=corpus_path
        )
        return RunManager(cfg, *components)

    _results, summary = asyncio.run(
        run_benchmark(
            cases,
            make_manager,
            output_dir=output_dir,
            max_concurrency=cfg.benchmark.max_concurrency,
        )
    )

    typer.echo(f"\nBenchmark complete: {summary['total_cases']} cases")
    typer.echo(f"  experiment: {experiment_id}")
    typer.echo(f"  avg task_success_rate: {summary.get('avg_task_success_rate', 0)}")
    typer.echo(f"  avg citation_coverage: {summary.get('avg_citation_coverage', 0)}")
    typer.echo(f"  avg elapsed: {summary.get('avg_elapsed_seconds', 0):.1f}s")
    typer.echo(f"\nResults: {output_dir / 'results.jsonl'}")
    typer.echo(f"Summary: {output_dir / 'summary.json'}")
