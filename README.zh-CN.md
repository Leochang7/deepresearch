# DeepResearch Agent

<div align="center">
  <h1>DeepResearch Agent</h1>
  <p>
    <strong>面向复杂深度研究任务的多智能体协作系统。</strong><br />
    规划任务、检索证据、共享记忆、修复报告、评测质量、追踪实验。
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

DeepResearch Agent 是一个面向长链路研究任务的自研多智能体系统。它把 DAG 任务规划、并行执行、跨语言 RAG、共享记忆、Red-Blue 对抗修复、规则评测、LLM-as-Judge、基准数据集和 Langfuse 可观测闭环组合在一起。

这个项目不是普通聊天应用，也不是简单 RAG demo。核心链路是：

```text
Planner -> DAG Executor -> Research Agent -> Retriever -> Memory -> Synthesizer -> Red/Blue/Judge -> Evaluator
```

## 从这里开始

| 你想做什么 | 去哪里 |
| --- | --- |
| 安装项目并跑真实研究任务 | [快速开始](#快速开始) |
| 配置真实模型、向量库、Langfuse | [配置项](#配置项) |
| 了解系统能力边界 | [功能面](#功能面) |
| 找主要代码目录 | [架构地图](#架构地图) |
| 跑 benchmark 和实验脚本 | [基准评测](#基准评测) |
| 跑测试和质量检查 | [验证](#验证) |
| 查看已知限制 | [注意事项](#注意事项) |

## 功能面

| 模块 | 能力 |
| --- | --- |
| 任务规划 | Planner Agent 将复杂问题拆解为 DAG 子任务，并支持有界 replan。 |
| 任务执行 | 异步 DAG Executor 并行执行 ready tasks，支持超时、重试、取消和失败隔离。 |
| 检索链路 | 本地语料、Tavily、MiMo Search、query 改写、BM25/keyword 召回、Milvus 向量召回、RRF 融合、reranker 精排和 MMR 选择。 |
| 共享记忆 | 基于 Milvus 的 run 级共享记忆，支持向量召回、关键词召回、快照导出、写入去重和轻量冲突检测。 |
| 报告生成 | Synthesizer 生成结构化 Markdown 报告，保留可追溯证据和限制说明。 |
| 对抗修复 | Red Agent 审查事实性、推理一致性和证据质量；Blue Agent 执行 ADD/DELETE/MODIFY/VERIFY 修复；Judge 控制收敛。 |
| 评测体系 | 规则指标、事实级匹配、幻觉标记、LLM-as-Judge 五维评分、Bootstrap 95% CI 和 Cohen's d。 |
| 数据集 | ResearchBench mini/full、多语言 benchmark 和 HotpotQA 深度研究变体。 |
| 可观测性 | Langfuse 提示词管理、数据集绑定、嵌套观测、指标上报和人工标注回流。 |

## 架构地图

| 路径 | 职责 |
| --- | --- |
| `src/deepresearch/agents/` | Planner、Researcher、Synthesizer、Red/Blue Agent、Judge 和通用 agent prompt helper。 |
| `src/deepresearch/core/` | DAG、执行器、状态机、run manager、预算追踪、trace 记录和 JSON 修复。 |
| `src/deepresearch/retrieval/` | Retriever 接口、本地资料集、搜索适配器、切片、去重、词法策略、融合和打分。 |
| `src/deepresearch/memory/` | Milvus 记忆存储、mock memory、记忆快照和冲突检测。 |
| `src/deepresearch/llm/` | LLMClient 抽象，以及 MiMo、DeepSeek、OpenAI-compatible、vLLM-compatible 和 mock 后端。 |
| `src/deepresearch/embeddings/` | EmbeddingClient 抽象，以及 OpenAI-compatible/mock embedding 后端。 |
| `src/deepresearch/rerankers/` | RerankerClient 抽象，以及 OpenAI-compatible/mock reranker 后端。 |
| `src/deepresearch/evaluation/` | 指标、benchmark runner、数据集、统计分析、对比工具、Langfuse adapter、人工标注和 retrieval ablation。 |
| `src/deepresearch/prompts/` | 本地 prompt 模板和 PromptProvider 实现。 |
| `src/deepresearch/schemas/` | 任务、证据、报告和评测输出的 Pydantic schema。 |
| `examples/bench/` | Benchmark JSONL 数据集和 manifest。 |
| `examples/corpus/` | 可复现 benchmark 使用的本地资料集。 |
| `docs/` | 产品、配置、benchmark、Langfuse、路线图、任务和工作日志文档。 |

## 环境要求

- Python 3.11+
- `uv`
- 真实向量库运行需要 Docker Milvus Standalone
- 可选：Langfuse，用于提示词管理、trace、score、dataset 和人工标注流程

## 快速开始

安装依赖：

```bash
uv sync
```

`deepresearch run` 默认使用真实模式。运行前请先配置真实模型、检索、embedding、reranker 和 Milvus：

```bash
uv run deepresearch run "分析 2024-2026 年开源 LLM Agent 框架的发展趋势"
```

真实运行默认使用保守并发：一次只跑一个 DAG task，单个 ResearchAgent task 内一次只发一个检索请求。只有在 provider 额度允许时再显式调高：

```bash
uv run deepresearch run "分析 2024-2026 年开源 LLM Agent 框架的发展趋势" --max-concurrency 2 --retrieval-concurrency 2
```

如果只是想跑不依赖 API key、互联网、Milvus 或 Langfuse 的离线 smoke demo，需要显式指定 mock 模式：

```bash
uv run deepresearch run "分析 2024-2026 年开源 LLM Agent 框架的发展趋势" --mode mock
```

输出保存在 `outputs/<run_id>/`：

| 文件 | 说明 |
| --- | --- |
| `report.md` | 最终结构化研究报告。 |
| `evaluation.json` | 规则指标、judge 分数和评测分层结果。 |
| `trace.jsonl` | 完整执行 trace。 |
| `memory_snapshot.jsonl` | 检索 chunk、证据和记忆元数据快照。 |

查看运行结果：

```bash
uv run deepresearch inspect <run_id>
uv run deepresearch inspect <run_id> --timeline
uv run deepresearch eval <run_id>
```

## 配置项

创建本地配置：

```bash
cp .env.example .env
cp config.example.toml config.toml
```

真实运行常用变量：

```dotenv
MIMO_API_KEY=your-key
TAVILY_API_KEY=your-key
DEEPRESEARCH_MILVUS_URI=http://localhost:19530
DEEPRESEARCH_EMBEDDING_BASE_URL=https://your-endpoint/v1
DEEPRESEARCH_EMBEDDING_API_KEY=your-key
DEEPRESEARCH_RERANKER_BASE_URL=https://your-endpoint/v1
DEEPRESEARCH_RERANKER_API_KEY=your-key
```

可选 Langfuse 变量：

```dotenv
DEEPRESEARCH_LANGFUSE_ENABLED=true
DEEPRESEARCH_PROMPT_PROVIDER=langfuse_with_local_fallback
DEEPRESEARCH_PROMPT_LABEL=production
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3000
```

检查真实环境：

```bash
uv run deepresearch doctor --real
```

启动 Milvus Standalone：

```bash
docker compose -f docker-compose.milvus.yml up -d
```

## 真实运行

使用 Tavily 搜索。因为 `run` 默认就是真实模式，`--mode real` 可以省略：

```bash
uv run deepresearch run "研究问题" --retriever tavily
```

使用 MiMo 原生搜索：

```bash
uv run deepresearch run "研究问题" --retriever mimo
```

使用本地语料，但 LLM、embedding、reranker 和 Milvus 仍走真实后端：

```bash
uv run deepresearch run "研究问题" --retriever local \
  --corpus ./examples/corpus
```

真实模式不会静默回退到 mock。缺少密钥或外部服务不可用时，应通过 `doctor` 或运行时报错尽早暴露。

## 基准评测

离线运行 smoke benchmark：

```bash
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode mock
```

运行可复现的真实 local-corpus benchmark：

```bash
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl \
  --mode real \
  --retriever local \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --output outputs/bench-local \
  --experiment local-corpus-smoke
```

并行运行 benchmark case：

```bash
uv run deepresearch benchmark examples/bench/multilingual_large20.jsonl \
  --mode mock \
  --max-concurrency 4
```

将本地 prompts 或 datasets 推送到 Langfuse：

```bash
uv run deepresearch prompts push --label staging
uv run deepresearch datasets push examples/bench/researchbench_mini.jsonl --name researchbench_mini
```

`scripts/experiments/` 中提供 local mock smoke、模型对比、prompt ablation、多语言回归和 full-suite 汇总脚本。

## 验证

默认测试完全离线，不依赖 API key、互联网、Milvus 或 Langfuse：

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

真实服务相关测试需要显式选择：

```bash
uv run pytest -m integration
uv run pytest -m milvus
uv run pytest -m network
uv run pytest -m llm
```

## 文档

- [English README](README.md)
- [文档入口](docs/README.md)
- [当前项目状态](docs/PROJECT_STATUS.md)
- [路线图](docs/ROADMAP.md)
- [任务状态](docs/TASKS.md)
- [工作日志](docs/WORKLOG.md)
- [配置说明](docs/CONFIGURATION.md)
- [真实 benchmark 指南](docs/REAL_BENCHMARK_GUIDE.md)
- [Langfuse 评测闭环设计](docs/EVALUATION_LANGFUSE_PLAN.md)
- [量化指标口径](docs/QUANTITATIVE_CLAIMS.md)

## 注意事项

- 不要提交 `.env`、API key、`outputs/`、缓存、临时实验文件或本地数据库。
- 稳定 benchmark 主路径使用本地语料。实时联网搜索适合演示，但不适合作为可复现基线。
- Langfuse 是可选能力。本地 prompts 继续作为离线 fallback 和测试基线。
- 真实运行的向量库目标是 Milvus Standalone；单元测试使用 mock。
- 完整真实 benchmark 会消耗真实 LLM、embedding、reranker 和搜索额度，并且耗时较长。
