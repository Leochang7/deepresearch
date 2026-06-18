# DeepResearch Agent

<div align="center">
  <h1>DeepResearch Agent</h1>
  <p>
    <strong>A multi-agent deep research system for complex research tasks.</strong><br />
    Plan tasks, retrieve evidence, share memory, repair reports, evaluate quality, and trace experiments.
  </p>
  <p>
    <a href="README.md">English</a> |
    <a href="README.zh-CN.md">简体中文</a>
  </p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB" />
    <img alt="Package manager" src="https://img.shields.io/badge/package-uv-6E56CF" />
    <img alt="Vector store" src="https://img.shields.io/badge/vector%20store-Milvus-00A1EA" />
    <img alt="Evaluation" src="https://img.shields.io/badge/evaluation-ResearchBench-2E7D32" />
    <img alt="Observability" src="https://img.shields.io/badge/observability-Langfuse-111827" />
  </p>
</div>

DeepResearch Agent is a self-built multi-agent system for long-form research. It combines DAG-based planning, parallel task execution, cross-lingual RAG, shared memory, Red-Blue adversarial repair, rule-based evaluation, LLM-as-Judge, benchmark datasets, and Langfuse observability.

The project is not a chatbot wrapper or a simple RAG demo. Its core workflow is:

```text
Planner -> DAG Executor -> Research Agent -> Retriever -> Memory -> Synthesizer -> Red/Blue/Judge -> Evaluator
```

## Start Here

| Goal | Go to |
| --- | --- |
| Install and run a real research task | [Quick Start](#quick-start) |
| Configure real LLM, embedding, reranker, Milvus, and Langfuse | [Configuration](#configuration) |
| Understand the system capabilities | [Feature Surface](#feature-surface) |
| Find the main code directories | [Architecture Map](#architecture-map) |
| Run benchmarks and experiment scripts | [Benchmarks](#benchmarks) |
| Run tests and quality checks | [Validation](#validation) |
| Understand known limits | [Notes](#notes) |

## Feature Surface

| Module | Capability |
| --- | --- |
| Planning | Planner Agent decomposes complex questions into DAG task graphs and supports bounded replan. |
| Execution | Async DAG Executor runs ready tasks in parallel with timeout, retry, cancellation, and failure isolation. |
| Retrieval | Local corpus, Tavily, MiMo Search, query expansion, BM25/keyword recall, Milvus vector recall, RRF fusion, reranker, and MMR selection. |
| Memory | Run-level shared memory backed by Milvus, supporting vector recall, keyword recall, snapshot export, deduplication, and lightweight conflict detection. |
| Report generation | Synthesizer produces structured Markdown reports with traceable evidence and limitations. |
| Red-Blue review | Red Agent attacks factuality, reasoning, and evidence quality; Blue Agent applies ADD/DELETE/MODIFY/VERIFY fixes; Judge controls convergence. |
| Evaluation | Rule metrics, fact-level matching, hallucination flags, LLM-as-Judge five-dimensional scoring, Bootstrap 95% CI, and Cohen's d. |
| Benchmark suite | ResearchBench mini/full, multilingual benchmarks, and a HotpotQA-style deep-research variant. |
| Observability | Langfuse prompt management, dataset binding, nested observations, score reporting, and human annotation handoff. |

## Architecture Map

| Path | Responsibility |
| --- | --- |
| `src/deepresearch/agents/` | Planner, Researcher, Synthesizer, Red/Blue agents, Judge, and shared agent prompting helpers. |
| `src/deepresearch/core/` | DAG, executor, state machine, run manager, budget tracking, trace logging, and JSON repair. |
| `src/deepresearch/retrieval/` | Retriever interface, local dataset retrieval, search adapters, chunking, deduplication, lexical policy, fusion, and scoring. |
| `src/deepresearch/memory/` | Milvus memory store, mock memory, memory snapshot, and conflict detection. |
| `src/deepresearch/llm/` | LLM client abstraction and MiMo, DeepSeek, OpenAI-compatible, vLLM-compatible, and mock clients. |
| `src/deepresearch/embeddings/` | Embedding client abstraction and OpenAI-compatible/mock embeddings. |
| `src/deepresearch/rerankers/` | Reranker client abstraction and OpenAI-compatible/mock rerankers. |
| `src/deepresearch/evaluation/` | Metrics, benchmark runner, datasets, statistics, comparison tools, Langfuse adapter, annotation workflow, and retrieval ablation. |
| `src/deepresearch/prompts/` | Local prompt templates and PromptProvider implementations. |
| `src/deepresearch/schemas/` | Pydantic schemas for tasks, evidence, reports, and evaluation outputs. |
| `examples/bench/` | Benchmark JSONL datasets and manifest. |
| `examples/corpus/` | Local corpus documents for reproducible benchmark runs. |
| `docs/` | Product, configuration, benchmark, Langfuse, roadmap, task, and worklog documents. |

## Requirements

- Python 3.11+
- `uv`
- Docker Milvus Standalone for real vector-store runs
- Optional: Langfuse for prompt management, trace, scores, datasets, and annotation workflow

## Quick Start

Install dependencies:

```bash
uv sync
```

By default, `deepresearch run` uses real mode. Make sure the real-run variables are configured before running:

```bash
uv run deepresearch run "Analyze the development trend of open-source LLM agent frameworks from 2024 to 2026"
```

Real runs use conservative concurrency by default: one DAG task at a time and one retriever request per ResearchAgent task. Increase it explicitly only when the provider quota can handle it:

```bash
uv run deepresearch run "Analyze the development trend of open-source LLM agent frameworks from 2024 to 2026" --max-concurrency 2 --retrieval-concurrency 2
```

For an offline smoke demo that does not require API keys, internet, Milvus, or Langfuse, explicitly use mock mode:

```bash
uv run deepresearch run "Analyze the development trend of open-source LLM agent frameworks from 2024 to 2026" --mode mock
```

Outputs are written to `outputs/<run_id>/`:

| File | Description |
| --- | --- |
| `report.md` | Final structured research report. |
| `evaluation.json` | Rule metrics, judge scores, and evaluation layers. |
| `trace.jsonl` | Full execution trace. |
| `memory_snapshot.jsonl` | Retrieved chunks, evidence, and memory metadata snapshot. |

Inspect a run:

```bash
uv run deepresearch inspect <run_id>
uv run deepresearch inspect <run_id> --timeline
uv run deepresearch eval <run_id>
```

## Configuration

Create local config files:

```bash
cp .env.example .env
cp config.example.toml config.toml
```

Common real-run variables:

```dotenv
MIMO_API_KEY=your-key
TAVILY_API_KEY=your-key
DEEPRESEARCH_MILVUS_URI=http://localhost:19530
DEEPRESEARCH_EMBEDDING_BASE_URL=https://your-endpoint/v1
DEEPRESEARCH_EMBEDDING_API_KEY=your-key
DEEPRESEARCH_RERANKER_BASE_URL=https://your-endpoint/v1
DEEPRESEARCH_RERANKER_API_KEY=your-key
```

Optional Langfuse variables:

```dotenv
DEEPRESEARCH_LANGFUSE_ENABLED=true
DEEPRESEARCH_PROMPT_PROVIDER=langfuse_with_local_fallback
DEEPRESEARCH_PROMPT_LABEL=production
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3000
```

Check real environment readiness:

```bash
uv run deepresearch doctor --real
```

Start Milvus Standalone:

```bash
docker compose -f docker-compose.milvus.yml up -d
```

## Real Runs

Run with Tavily web search. Since `run` defaults to real mode, `--mode real` is optional:

```bash
uv run deepresearch run "Research question" --retriever tavily
```

Run with MiMo native search:

```bash
uv run deepresearch run "Research question" --retriever mimo
```

Run against a local corpus while still using real LLM, embedding, reranker, and Milvus:

```bash
uv run deepresearch run "Research question" --retriever local \
  --corpus ./examples/corpus
```

Real mode does not silently fall back to mock clients. Missing keys or unavailable services should fail early through `doctor` or runtime errors.

## Benchmarks

Run the default smoke benchmark offline:

```bash
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode mock
```

Run a reproducible real local-corpus benchmark:

```bash
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl \
  --mode real \
  --retriever local \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --output outputs/bench-local \
  --experiment local-corpus-smoke
```

Run benchmark cases in parallel:

```bash
uv run deepresearch benchmark examples/bench/multilingual_large20.jsonl \
  --mode mock \
  --max-concurrency 4
```

Push local prompts or datasets to Langfuse:

```bash
uv run deepresearch prompts push --label staging
uv run deepresearch datasets push examples/bench/researchbench_mini.jsonl --name researchbench_mini
```

Experiment scripts live in `scripts/experiments/` and cover local mock smoke, model comparison, prompt ablation, multilingual regression, and full-suite summary generation.

## Validation

Default tests are offline and should not require API keys, internet, Milvus, or Langfuse:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

Integration and real-service checks are opt-in:

```bash
uv run pytest -m integration
uv run pytest -m milvus
uv run pytest -m network
uv run pytest -m llm
```

## Documentation

- [中文 README](README.zh-CN.md)
- [Documentation index](docs/README.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Tasks](docs/TASKS.md)
- [Worklog](docs/WORKLOG.md)
- [Configuration](docs/CONFIGURATION.md)
- [Real benchmark guide](docs/REAL_BENCHMARK_GUIDE.md)
- [Langfuse evaluation plan](docs/EVALUATION_LANGFUSE_PLAN.md)
- [Quantitative claims](docs/QUANTITATIVE_CLAIMS.md)

## Notes

- Do not commit `.env`, API keys, `outputs/`, caches, temporary experiment files, or local databases.
- The stable benchmark path uses local corpus datasets. Real-time web search is useful for demos but is not deterministic enough for baseline evaluation.
- Langfuse is optional. Local prompts remain the offline fallback and test baseline.
- Milvus Standalone is the supported vector-store target for real runs; unit tests use mocks.
- Full real benchmark suites can be slow and consume real LLM, embedding, reranker, and search credits.
