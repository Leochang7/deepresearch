# AGENTS.md

本文件面向 AI coding agents。进入本仓库后，先阅读本文件，再阅读 `README.md` 和相关 `docs/*.md`。执行任务时以本文件规则为准。

## 1. 项目定位

DeepResearch Agent 是一个面向复杂深度研究任务的多智能体协作系统。核心价值是自研多 Agent DAG 编排、任务状态机、动态 replan、Milvus 记忆层、Red-Blue 对抗修复和评测闭环。

不要把项目做成普通聊天应用或简单 RAG demo。

核心链路：

```text
Planner -> DAG Executor -> Research Agent -> Retriever -> Memory -> Synthesizer -> Red/Blue/Judge -> Evaluator
```

## 2. 硬性规则

- 必须使用 `uv run ...` 执行 Python 工具，不要直接使用 `python ...`、`pip ...`、`pytest ...`、`ruff ...`。
- 不要使用 LangChain、LangGraph、CrewAI、AutoGen 作为核心编排层。
- Agent 框架只能作为可选 adapter 或 baseline，放在 `adapters/` 或 `experiments/baselines/`。
- 核心 DAG Executor、状态机、replan、降级策略、Memory、Retriever、Red-Blue 和 Evaluator 必须保持自研。
- 不要提交 `.env`、密钥、`outputs/`、缓存、临时实验文件或本地数据库。
- 不要自动 commit，除非用户明确要求。
- 不要绕过失败的测试或质量检查；修复失败，或在最终回复中明确说明阻塞原因和未覆盖风险。

## 3. 目录结构

采用 `src/` 布局。业务代码只放在 `src/deepresearch/`。

```text
src/deepresearch/
  agents/
    planner.py
    researcher.py
    synthesizer.py
    red_agent.py
    blue_agent.py
    judge.py
  core/
    dag.py
    executor.py
    state.py
    run_manager.py
    trace.py
  memory/
    store.py
    embeddings.py
    milvus_store.py
    conflict.py
  retrieval/
    base.py
    local_dataset.py
    tavily_search.py
    web_search.py
    mimo_search.py
    fetcher.py
    chunking.py
    dedup.py
    browser.py
    mcp.py
    model_native.py
  llm/
    base.py
    mimo.py
    openai_compatible.py
    deepseek.py
    mock.py
  embeddings/
    base.py
    openai_compatible.py
    mock.py
  rerankers/
    base.py
    openai_compatible.py
    mock.py
  evaluation/
    metrics.py
    judge_eval.py
    benchmark.py
  schemas/
    task.py
    evidence.py
    report.py
    evaluation.py
  prompts/
    planner.md
    researcher.md
    synthesizer.md
    red_agent.md
    blue_agent.md
tests/
docs/
examples/
  corpus/
outputs/
```

目录职责：

- `src/deepresearch/agents/`：Agent 行为逻辑。
- `src/deepresearch/core/`：DAG、状态机、执行器、run 生命周期、trace。
- `src/deepresearch/memory/`：Milvus MemoryStore、embedding、去重、冲突检测。
- `src/deepresearch/retrieval/`：统一 Retriever 接口及本地资料集、搜索、浏览器、MCP、模型原生搜索适配。
- `src/deepresearch/llm/`：LLMClient 抽象和模型后端实现。
- `src/deepresearch/embeddings/`：EmbeddingClient 抽象和 Qwen/OpenAI-compatible 后端。
- `src/deepresearch/rerankers/`：RerankerClient 抽象和 bge/OpenAI-compatible 后端。
- `src/deepresearch/evaluation/`：规则指标、LLM-as-Judge、benchmark。
- `src/deepresearch/schemas/`：Pydantic schema 和 enum。
- `src/deepresearch/prompts/`：稳定 prompt 模板。
- `tests/`：测试代码。
- `docs/`：产品、设计、任务和实现文档。
- `examples/corpus/`：本地资料集。
- `outputs/`：运行产物，不提交。

## 4. 命名规范

- Python 文件和模块使用 `snake_case.py`。
- 类名使用 `PascalCase`，例如 `MilvusMemoryStore`、`LocalDatasetRetriever`。
- 函数、变量、字段使用 `snake_case`。
- 常量使用 `UPPER_SNAKE_CASE`。
- Pydantic schema 放在 `schemas/`，名称使用业务名词，例如 `TaskNode`、`EvidenceItem`、`ResearchReport`。
- 抽象基类使用清晰接口名，例如 `LLMClient`、`MemoryStore`、`Retriever`、`Evaluator`。
- 测试文件命名为 `test_<module>.py`。
- Prompt 文件命名为 `<agent_or_stage>.md`。
- 文档文件使用大写主题名或清晰英文名，例如 `PRD.md`、`RETRIEVAL_DESIGN.md`、`TASKS.md`。

## 5. 开发环境

使用 `uv` 管理环境和命令。

常用命令：

```bash
uv sync
uv run deepresearch --help
uv run ruff format .
uv run ruff check .
uv run pytest
```

依赖管理：

```bash
uv add <package>
uv add --dev <package>
uv lock
```

不要使用：

```bash
python ...
pip install ...
pytest
ruff check .
```

## 6. 环境变量与密钥

- 本地私密配置放 `.env`，不要提交。
- 仓库应维护 `.env.example`，只列变量名和空值，不放真实密钥。
- LLM、搜索 API、Milvus 配置必须从环境变量或配置文件读取。
- 测试默认使用 mock，不依赖真实 API key。

建议变量：

```env
DEEPRESEARCH_LLM_PROVIDER=mimo
DEEPRESEARCH_LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_API_KEY=
DEEPRESEARCH_LLM_MODEL=mimo-v2.5-pro
DEEPRESEARCH_EMBEDDING_BASE_URL=
DEEPRESEARCH_EMBEDDING_API_KEY=
DEEPRESEARCH_EMBEDDING_MODEL=Qwen3-Embedding-4B
DEEPRESEARCH_EMBEDDING_DIM=1024
DEEPRESEARCH_RERANKER_BASE_URL=
DEEPRESEARCH_RERANKER_API_KEY=
DEEPRESEARCH_RERANKER_MODEL=bge-reranker-v2-m32
DEEPRESEARCH_MILVUS_URI=http://localhost:19530
DEEPRESEARCH_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
```

## 7. Milvus 策略

- 开发、demo 和真实运行默认使用 Docker Milvus Standalone。
- MVP 使用 `deepresearch_chunks` 和 `deepresearch_memories` 两个 collection。
- 向量字段为 `embedding: FloatVector(1024)`，metric type 为 `COSINE`，index type 为 `HNSW`。
- 单元测试不得依赖真实 Milvus，必须使用 `MockMemoryStore` 或等价测试替身。
- 集成测试可以依赖 Milvus，但必须使用 marker 区分。
- 没有 Milvus 服务时，基础测试仍必须能跑；真实运行前先启动 `docker-compose.milvus.yml`。

## 8. Retriever 策略

Research Agent 只依赖统一 `Retriever` 接口，不直接调用搜索 API、MCP 或模型原生搜索。

MVP 必须支持：

- `LocalDatasetRetriever`
- `WebSearchRetriever` with Tavily provider
- `MiMoSearchRetriever`
- mock 搜索后端
- `httpx + trafilatura` 轻量正文抓取

后续再接：

- `BrowserRetriever`
- `MCPRetriever`
- `ModelNativeSearchRetriever`

默认测试不得依赖互联网。Tavily 搜索、MiMo 搜索、embedding/reranker 真实 endpoint、浏览器抓取、MCP、模型原生搜索必须作为 integration/e2e 测试处理。

## 8.1 模型策略

- 默认 Chat/Planner/Research/Synthesizer/Red-Blue/Judge 模型为 MiMo v2.5 Pro。
- MiMo 原生搜索必须通过 `MiMoSearchRetriever` 接入。
- MiMo API 使用 OpenAI-compatible `/chat/completions`，鉴权 header 为 `api-key`。
- DeepSeek 仅作为 fallback chat 后端或对比实验后端。
- embedding 使用 Qwen3-Embedding-4B，维度固定为 1024。
- Qwen3-Embedding-4B 默认 L2 归一化，系统层默认不重复 normalize。
- reranker 使用 bge-reranker-v2-m32。
- 业务模块不得直接依赖具体模型 SDK，必须走 `LLMClient`、`EmbeddingClient`、`Reranker`、`Retriever` 等接口。

## 8.2 Chunk、去重与成本控制

- MVP chunk 参数：`chunk_size_chars = 1200`，`chunk_overlap_chars = 200`，`min_chunk_chars = 300`。
- MVP 去重策略：`source_url + content_hash`。
- 默认限制：`max_queries_per_task = 5`，`max_docs_per_task = 20`，`max_chunks_per_task = 80`，`max_llm_calls_per_run = 80`。
- 超过限制时必须记录 trace，并优雅降级，不要让单个 run 无限扩张。

## 9. 文档规范、计划与任务记录

AI agent 必须维护项目状态文档。文档入口和详细规范见 `docs/README.md`。

文档分层：

- `README.md`：用户入口，只放安装、快速开始、常用命令、核心架构和文档索引。
- `docs/README.md`：文档入口，说明各文档职责、唯一事实源和整理规则。
- `docs/PROJECT_STATUS.md`：当前项目状态唯一摘要，回答“现在做到哪、下一步做什么、主要限制是什么”。
- `docs/ROADMAP.md`：路线图唯一维护入口，只记录当前和未来方向；历史路线归档到 `docs/archive/`。
- `docs/TASKS.md`：任务状态唯一来源，使用 `- [ ]` 和 `- [x]` 维护 backlog、完成标准和验证命令。
- `docs/WORKLOG.md`：全量操作日志，记录关键决策、验证结果、阻塞点和完成记录。
- `docs/CONFIGURATION.md`：配置项、环境变量、真实运行配置和默认值。
- `docs/REAL_BENCHMARK_GUIDE.md`：真实 benchmark、local corpus smoke、指标解释和复现方式。
- `docs/EVALUATION_LANGFUSE_PLAN.md`：Langfuse adapter、benchmark runner、LLM-as-Judge 和评测闭环设计。

唯一事实源：

- 当前状态以 `docs/PROJECT_STATUS.md` 为准。
- 路线规划以 `docs/ROADMAP.md` 为准。
- 任务状态以 `docs/TASKS.md` 为准。
- 操作历史以 `docs/WORKLOG.md` 为准。
- 配置项以 `docs/CONFIGURATION.md` 和 `.env.example` 为准。
- 评测复现方式以 `docs/REAL_BENCHMARK_GUIDE.md` 为准。
- Langfuse 评测设计以 `docs/EVALUATION_LANGFUSE_PLAN.md` 为准。

维护规则：

- 对于超过一个文件或预计超过 30 分钟的任务，先在设计文档或 `docs/TASKS.md` 中记录计划。
- 必须维护 `docs/TASKS.md`，使用 `- [ ]` 和 `- [x]` 标记任务状态。
- 每完成一个 task，立即更新 `docs/TASKS.md`。
- 长任务、重要修复、真实验收、失败阻塞和阶段完成都要更新 `docs/WORKLOG.md`。
- `docs/WORKLOG.md` 保存全量操作日志，新记录必须追加到文件最底部，不删除历史记录。
- 不要把模型临时思考过程写入文档；只记录决策、任务状态、验证结果和阻塞点。
- 复杂功能可以创建 `docs/tasks/<feature>.md`。
- `docs/TASKS.md` 太长时，归档到 `docs/tasks/archive-YYYYMM.md`。
- 不要在多个文档重复维护同一任务状态；如冲突，以 `docs/TASKS.md` 为准。
- 不要把同一段完整规划复制到多个文档；其他文档只保留摘要和链接。
- 过期但仍有追溯价值的设计优先移动到 `docs/archive/`，不要留在主文档区制造多版本事实。

## 10. 文档同步规则

以下改动必须同步更新文档：

- 目录结构变化。
- 常用命令变化。
- 配置项或环境变量变化。
- 核心接口变化。
- 数据 schema 变化。
- 状态机变化。
- Milvus collection schema 变化。
- Retriever 行为变化。
- Red-Blue 或 Evaluator 行为变化。

纯 bugfix、测试补充、内部重构如果不改变对外行为，可以不更新文档。

## 11. 测试与质量保障

默认测试必须离线可跑：

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

集成测试和端到端测试使用 marker：

```bash
uv run pytest -m integration
uv run pytest -m e2e
uv run pytest -m milvus
uv run pytest -m network
uv run pytest -m llm
```

规则：

- `uv run pytest` 必须能在无 API key、无互联网、无外部服务时通过。
- 调真实 LLM、Tavily、MiMo 搜索、embedding/reranker endpoint、真实浏览器抓取、真实 Milvus Standalone 的测试必须标记为 `integration` 或 `e2e`。
- 固定 marker：`unit`、`integration`、`e2e`、`slow`、`network`、`milvus`、`llm`。
- 网络调用必须通过接口 mock。
- 异步代码使用 `pytest-asyncio`。
- 涉及 DAG Executor、Retriever、Memory、Milvus、Red-Blue、Evaluator 的改动必须补对应测试。
- 如果质量命令无法运行，最终回复必须说明原因和风险。

## 12. 提交规范

采用 Conventional Commits。commit message 使用英文。

示例：

```text
feat: add milvus memory store
fix: handle failed retriever fallback
docs: update mvp roadmap
test: cover dag executor timeout
refactor: split retriever interface
chore: update uv dependencies
```

规则：

- 一次 commit 只做一类事情。
- 提交前必须跑质量命令。
- 不要提交 `outputs/`、`.env`、缓存、临时实验结果。
- AI agent 不要自动 commit，除非用户明确要求。

## 13. 分支策略

- `main`：稳定分支，只合入通过测试的可运行版本。
- `develop`：默认开发分支，AI agent 日常任务在这里进行。
- `feature/<short-name>`：复杂功能或高风险改动使用独立功能分支。
- 不直接在 `main` 上开发，除非用户明确要求。
- 合并到 `main` 前必须通过：

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

注意：仓库没有任何 commit 时，Git 还没有真实分支引用。第一次 commit 后再创建 `develop`：

```bash
git checkout -b develop
```

## 14. 完成任务前检查

完成任何代码任务前，按顺序检查：

1. 是否遵守 `uv run ...`。
2. 是否更新 `docs/TASKS.md`。
3. 是否需要同步更新设计文档。
4. 是否新增或更新测试。
5. 是否运行：

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

6. 是否有未说明的失败、跳过测试或外部依赖风险。
