# 技术栈与工程选型

## 1. 推荐技术栈

### 1.1 语言与运行时

- Python 3.11+
- `uv` 管理依赖和运行环境
- `asyncio` 实现异步调度

理由：

- Python 适合 LLM、RAG、评测和数据处理。
- `asyncio` 足够支撑 MVP 的 DAG 并发执行。
- `uv` 启动快、锁依赖方便，适合个人项目展示。

### 1.2 数据模型与校验

- Pydantic v2
- Python `Enum`
- `dataclasses` 或 Pydantic BaseModel

用途：

- 校验 Planner、Research Agent、Red Agent 的结构化输出。
- 定义任务状态、证据、报告、评测结果。
- 降低 LLM JSON 输出不稳定带来的风险。

### 1.3 LLM 后端

MVP：

- MiMo v2.5 Pro 作为默认 Chat/Planner/Research/Synthesis/Red-Blue/Judge 模型。
- MiMo 原生搜索通过 `MiMoSearchRetriever` 接入。
- DeepSeek 作为 fallback chat 后端保留。
- Qwen3-Embedding-4B 作为 embedding 模型，向量维度固定为 1024。
- bge-reranker-v2-m32 作为 reranker。
- OpenAI-compatible API 客户端。
- Mock LLM，用于测试和离线 demo。

后续：

- OpenAI。
- vLLM 本地部署。
- 其他 OpenAI-compatible 模型。

设计原则：

- 所有模型调用走统一 `LLMClient` 接口。
- embedding 和 reranker 分别走统一 `EmbeddingClient` 与 `RerankerClient` 接口。
- 不在业务代码中绑定具体模型厂商。
- Prompt 与模型参数可配置。
- 默认模型可以是 MiMo v2.5 Pro，但业务模块不得直接依赖 MiMo SDK。
- MiMo 使用 OpenAI-compatible `/chat/completions` 路径，但鉴权 header 为 `api-key`。

### 1.4 检索与数据源

MVP：

- 本地 Markdown/JSONL 资料集。
- Tavily 真实 Web 搜索 API。
- mock 搜索后端。
- MiMo 原生搜索适配器。
- MVP 使用 `httpx + trafilatura` 做轻量网页正文抓取。
- 统一 `Retriever` 接口。

后续：

- SerpAPI、Bing Search API、Brave Search API。
- Playwright 抓取动态网页正文。
- readability-lxml 清洗正文。
- MCP 工具适配层。
- 其他模型原生搜索适配层。

MVP 必须支持本地资料集，因为可复现、成本低、测试稳定；同时要支持 Tavily 真实搜索、MiMo 原生搜索和轻量正文抓取。MCP 不作为核心依赖，通过 `MCPRetriever` 作为后续插件接入。

### 1.5 记忆与索引

MVP：

- Milvus 作为主向量数据库。
- Docker 部署的 Milvus Standalone 用于开发、demo 和真实运行。
- MVP 使用 `deepresearch_chunks` 和 `deepresearch_memories` 两个 collection。
- 向量字段统一为 `embedding: FloatVector(1024)`。
- metric type 使用 `COSINE`。
- index type 使用 `HNSW`。
- 基于向量相似度 + 标量过滤完成语义记忆召回。

后续：

- Milvus Distributed。
- PostgreSQL 作为结构化分析库。
- 对接 Prometheus/Grafana 做 Milvus 运行监控。
- 增加 Qdrant 或 pgvector 作为可插拔备选后端。

选择理由：

- 项目定位是多 Agent 深度研究系统，语义记忆和证据召回是核心能力，直接使用专业向量数据库更贴合项目定位。
- Milvus 支持向量检索、标量字段过滤、多种索引和从单机到分布式的演进路径。
- 后续可以通过 `MemoryStore` 接口保留 Qdrant、pgvector 或本地 mock 后端，避免业务逻辑绑定 Milvus SDK。

### 1.6 文本处理与压缩

MVP：

- 简单 chunk。
- token 长度控制。
- 去重。
- 默认 chunk size 为 1200 chars，overlap 为 200 chars，最小 chunk 为 300 chars。
- MVP 去重使用 `source_url + content_hash`。

后续：

- TextRank。
- MMR。
- embedding 粗筛 + 关键词过滤 + 原文保留。

建议分层：

- L1：embedding 粗过滤。
- L2：TextRank/MMR 细筛。
- L3：关键证据原文保留。

### 1.7 评测与实验

MVP：

- pytest。
- 自定义规则指标。
- JSON/Markdown 实验结果。

后续：

- pandas。
- scipy。
- numpy。
- matplotlib 或 plotly。
- LLM-as-Judge。

指标：

- 任务成功率。
- 引用覆盖率。
- 报告结构完整度。
- 幻觉风险。
- 五维 Judge 评分。
- Bootstrap 95% CI。
- Cohen's d。

### 1.8 CLI 与配置

- Typer 或 argparse。
- TOML。
- Rich 输出进度和表格。

推荐：

- MVP 用 Typer + Rich。
- 配置文件用 TOML。
- 配置值优先级：CLI 参数 > 配置文件中的显式字段 > 环境变量 > 内置默认值。
- 配置文件路径优先级：`--config` > `DEEPRESEARCH_CONFIG_PATH` > `./config.toml` > `~/.config/deepresearch/config.toml` > `/etc/deepresearch/config.toml` > 内置默认值。

核心命令：

```bash
uv run deepresearch init
uv run deepresearch run "question"
uv run deepresearch index-corpus
uv run deepresearch eval <run_id>
uv run deepresearch inspect <run_id>
uv run deepresearch config
```

### 1.9 日志与可观察性

- Python `logging`。
- JSONL trace。
- 每个 run 单独输出目录。
- trace 使用 `outputs/<run_id>/trace.jsonl`，一行一个结构化事件。

输出结构：

```text
outputs/
  <run_id>/
    config.toml
    plan.json
    trace.jsonl
    memory_snapshot.jsonl
    report.draft.md
    report.final.md
    red_review.json
    evaluation.json
```

## 2. 不建议 MVP 使用的技术

- Celery：MVP 不需要分布式队列。
- Kubernetes：展示成本高于收益。
- LangGraph：可以参考思想，但自研 DAG 执行器更能体现项目亮点。
- 大型前端框架：MVP 阶段 CLI 更快闭环。
- Milvus Distributed：MVP 先用 Standalone，避免一开始引入 K8s 和多节点运维。
- 额外向量数据库：Qdrant、pgvector、FAISS 暂不作为主线，避免检索层过早分叉。

## 3. 推荐依赖清单

```toml
dependencies = [
  "pydantic>=2.0",
  "typer>=0.12",
  "rich>=13.0",
  "httpx>=0.27",
  "trafilatura>=1.8",
  "pymilvus>=2.4",
  "numpy>=1.26",
  "tomli-w>=1.0",
]

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "ruff>=0.5",
]
```

后续再加入：

```toml
dependencies = [
  "scipy",
  "pandas",
  "scikit-learn",
  "playwright",
  "mcp",
]
```

## 4. 架构选型原则

- 接口先行：LLM、Memory、Retriever、Evaluator 都通过接口调用。
- 可测试优先：核心逻辑必须能用 Mock LLM 测试。
- 可降级：失败任务不能直接拖垮整个研究流程。
- 可观测：每一步状态变化都写 trace。
- 少依赖框架：把项目亮点留给自研编排、记忆和评测闭环。

## 5. 版本规划中的技术演进

### MVP

- Python + asyncio + Milvus Standalone + Typer。
- 单机执行，Milvus Standalone 作为本地向量服务。
- MiMo v2.5 Pro + DeepSeek fallback + Mock LLM。
- Qwen3-Embedding-4B 1024 维 embedding。
- bge-reranker-v2-m32 reranker。
- LocalDatasetRetriever + Tavily WebSearchRetriever + MiMoSearchRetriever + mock 搜索后端。
- `httpx + trafilatura` 轻量正文抓取。

### V0.2

- 引入多后端 LLM。
- 引入更稳定的正文抽取。
- 完善 JSON fallback。
- 增强 Milvus collection schema、标量过滤、混合召回和去重策略。
- 增加 BrowserRetriever。
- 保持 Docker 部署 Milvus Standalone。

### V0.3

- 引入 ResearchBench。
- 增加 LLM-as-Judge。
- 增加实验脚本和统计分析。
- 引入 PostgreSQL 作为结构化实验与 trace 分析库。
- 增加 MCPRetriever 和 ModelNativeSearchRetriever。

### V0.4

- 增加 Web Demo。
- 增加 DAG 可视化。
- 增加报告 diff 和 Red-Blue 过程展示。
- 评估是否从 Milvus Standalone 迁移到 Milvus Distributed。
