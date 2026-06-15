# DeepResearch Agent

面向复杂深度研究任务的多智能体协作系统。

## 安装

```bash
git clone https://github.com/Leochang7/deepresearch.git
cd deepresearch
uv sync
```

## 快速开始

### Mock 运行（无需 API key）

```bash
uv run deepresearch run "分析 2024-2026 年开源 LLM Agent 框架的发展趋势"
```

输出保存在 `outputs/<run_id>/`：
- `report.md` — 结构化研究报告
- `evaluation.json` — 评测指标
- `trace.jsonl` — 执行 trace
- `memory_snapshot.jsonl` — 本次运行的 chunk、证据和元数据快照

### 配置

```bash
# 查看当前配置
uv run deepresearch config

# 使用自定义配置文件
uv run deepresearch run "问题" --config ./config.toml

# 复制示例配置
cp .env.example .env
cp config.example.toml config.toml
```

### 真实运行

真实模式不会静默回退到 Mock。先设置 API key 和 OpenAI-compatible
embedding/reranker endpoint：

```env
MIMO_API_KEY=your-key
TAVILY_API_KEY=your-key
DEEPRESEARCH_EMBEDDING_BASE_URL=https://your-endpoint/v1
DEEPRESEARCH_EMBEDDING_API_KEY=your-key
DEEPRESEARCH_RERANKER_BASE_URL=https://your-endpoint/v1
DEEPRESEARCH_RERANKER_API_KEY=your-key
```

如果 endpoint 的 `/models` 返回 `Qwen3-Embedding-4B` 为 2560 维，需同步设置：

```env
DEEPRESEARCH_EMBEDDING_DIM=2560
DEEPRESEARCH_RERANKER_MODEL=bge-reranker-v2-m3
```

```bash
# Tavily 搜索
uv run deepresearch run "研究问题" --mode real --retriever tavily

# MiMo 原生搜索
uv run deepresearch run "研究问题" --mode real --retriever mimo

# 本地语料检索，LLM/embedding/reranker 仍使用真实后端
uv run deepresearch run "研究问题" --mode real --retriever local \
  --corpus ./examples/corpus
```

### CLI 命令

```bash
uv run deepresearch run "研究问题" --mode mock
uv run deepresearch init --output config.toml
uv run deepresearch index-corpus ./examples/corpus --mode mock
uv run deepresearch eval <run_id>         # 查看评测结果
uv run deepresearch inspect <run_id>      # 查看 trace
uv run deepresearch inspect <run_id> --timeline
uv run deepresearch config                # 查看当前配置
```

`index-corpus` 会切片、生成 embedding，并写入配置中的 Milvus。
使用自定义运行根目录时，`eval` 和 `inspect` 可传
`--output-root <directory>`。

真实环境的复现配置、验收指标和已知限制见
[`docs/MVP_ACCEPTANCE.md`](docs/MVP_ACCEPTANCE.md)。

### Milvus Standalone

真实模式默认连接本机 Milvus Standalone：

```bash
docker compose -f docker-compose.milvus.yml up -d
```

默认地址为 `http://localhost:19530`，可通过
`DEEPRESEARCH_MILVUS_URI` 或 `config.toml` 覆盖。

## 测试

```bash
# 运行全部测试（离线，无需 API key）
uv run pytest

# 代码格式检查
uv run ruff check .
uv run ruff format .

# 集成测试（需要外部服务）
uv run pytest -m milvus
uv run pytest -m llm
uv run pytest -m network
```

## 核心架构

```
Planner → DAG Executor → Research Agent → Retriever → Memory → Synthesizer → Red/Blue/Judge → Evaluator
```

- **Planner**：将复杂问题拆解为 DAG 子任务
- **DAG Executor**：基于 asyncio 异步并发执行，支持 timeout/retry/replan
- **Research Agent**：query 生成 → retrieve → chunk → evidence 抽取
- **Memory**：Milvus 向量存储，支持语义召回
- **Synthesizer**：生成带 `[E12]` 引用的 Markdown 报告
- **Red/Blue**：Red 审查 issues，Blue 修复报告，Judge 驱动循环
- **Evaluator**：6 项规则指标；Red Agent 复审分数由 Judge 单独记录

## 技术栈

- Python 3.11+，`uv` 管理依赖
- Pydantic v2，asyncio
- MiMo v2.5 Pro / DeepSeek（LLM）
- Qwen3-Embedding-4B（embedding）
- bge-reranker-v2-m32（reranker）
- Milvus Standalone（向量存储）
- Tavily（Web 搜索）
- httpx + trafilatura（正文抓取）

## 文档

- [PRD：产品需求文档](docs/PRD.md)
- [MVP 范围与后续路线](docs/MVP_AND_ROADMAP.md)
- [Post-MVP Roadmap](docs/POST_MVP_ROADMAP.md)
- [技术栈与工程选型](docs/TECH_STACK.md)
- [检索与资料获取设计](docs/RETRIEVAL_DESIGN.md)
- [配置设计](docs/CONFIGURATION.md)
- [任务状态](docs/TASKS.md)
- [工作日志](docs/WORKLOG.md)
