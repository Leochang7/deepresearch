# Tasks

项目级任务状态文件。AI agent 每完成一个 task 后必须更新本文件。只保留近期 MVP backlog、最近完成记录和阻塞项；复杂功能可拆到 `docs/tasks/<feature>.md`。

规则：

- 使用 `- [ ]` 和 `- [x]` 标记状态。
- 每完成一个 task，立即更新本文件。
- 不要把临时思考写进本文件，只记录任务状态、验收标准和阻塞点。
- 默认验证命令必须使用 `uv run ...`。

## MVP Backlog

### M0 文档与工程约束

- [x] T000 建立项目规划文档
  - Files: `README.md`, `docs/PRD.md`, `docs/MVP_AND_ROADMAP.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/TECH_STACK.md`, `docs/RETRIEVAL_DESIGN.md`, `docs/CONFIGURATION.md`
  - Done when: 项目定位、MVP、技术栈、Retriever、配置规则已明确。
  - Verify: 文档人工检查。

- [x] T001 建立 AI 开发约束
  - Files: `AGENTS.md`, `docs/TASKS.md`, `docs/WORKLOG.md`
  - Done when: 目录结构、命名规范、提交规范、uv 命令、测试规则、任务记录规则已明确。
  - Verify: 文档人工检查。

### M1 项目骨架与工具链

- [x] T009 创建 `develop` 开发分支
  - Files: `.git`
  - Done when: 仓库已有初始 commit，且存在 `main` 和 `develop` 两个分支，日常开发切到 `develop`。
  - Verify: `git branch --list`

- [x] T010 建立 `src/deepresearch/` 包结构
  - Files: `src/deepresearch/**/__init__.py`
  - Done when: AGENTS.md 中定义的包目录全部存在，空包可导入。
  - Verify: `uv run pytest`

- [x] T011 配置项目依赖和 CLI entry
  - Files: `pyproject.toml`, `src/deepresearch/cli.py`
  - Done when: `deepresearch` 命令可通过 uv 启动并显示 help。
  - Verify: `uv run deepresearch --help`

- [x] T012 配置 Ruff、pytest、pytest-asyncio 和测试 markers
  - Files: `pyproject.toml`, `tests/`
  - Done when: `unit`、`integration`、`e2e`、`slow`、`network`、`milvus`、`llm` markers 已注册。
  - Verify: `uv run ruff check .` and `uv run pytest`

- [x] T013 增加 `.env.example` 和默认配置模板
  - Files: `.env.example`, `config.example.toml`
  - Done when: 所有 `docs/CONFIGURATION.md` 中列出的变量都有示例值或空值。
  - Verify: 文档人工检查。

### M2 配置、Schema 与 Trace

- [x] T020 实现配置加载
  - Files: `src/deepresearch/config.py`, `tests/test_config.py`
  - Done when: 支持 `--config`、`DEEPRESEARCH_CONFIG_PATH`、当前目录、用户目录、系统目录和内置默认值；配置值优先级为 CLI > env > file > default。
  - Verify: `uv run pytest tests/test_config.py`

- [x] T021 定义核心 schema
  - Files: `src/deepresearch/schemas/*.py`, `tests/schemas/`
  - Done when: `TaskNode`、`ResearchPlan`、`RetrievedDocument`、`EvidenceItem`、`ResearchReport`、`EvaluationResult` schema 可校验。
  - Verify: `uv run pytest tests/schemas`

- [x] T022 实现 TaskState 和状态流转校验
  - Files: `src/deepresearch/core/state.py`, `tests/core/test_state.py`
  - Done when: 9 状态枚举和合法流转表实现；非法流转抛出明确异常。
  - Verify: `uv run pytest tests/core/test_state.py`

- [x] T023 实现 JSON fallback
  - Files: `src/deepresearch/core/json_repair.py`, `tests/core/test_json_repair.py`
  - Done when: 支持 strict JSON、Markdown json code block、首个对象/数组截取、去尾逗号、中文引号替换、缺失字段默认值。
  - Verify: `uv run pytest tests/core/test_json_repair.py`

- [x] T024 实现 TraceLogger
  - Files: `src/deepresearch/core/trace.py`, `tests/core/test_trace.py`
  - Done when: trace 以 JSONL 追加写入，支持 task、retriever、milvus、llm、red-blue、evaluation 事件类型。
  - Verify: `uv run pytest tests/core/test_trace.py`

### M3 模型抽象

- [x] T030 实现 LLMClient 抽象和 MockLLM
  - Files: `src/deepresearch/llm/base.py`, `src/deepresearch/llm/mock.py`, `tests/llm/`
  - Done when: mock 能返回稳定 planner/research/red-blue 输出。
  - Verify: `uv run pytest tests/llm`

- [x] T031 实现 MiMo v2.5 Pro LLMClient
  - Files: `src/deepresearch/llm/mimo.py`, `tests/llm/test_mimo.py`
  - Done when: 使用 OpenAI-compatible `/chat/completions`，header 为 `api-key`，支持 thinking disabled、temperature、top_p、max_completion_tokens。
  - Verify: `uv run pytest tests/llm/test_mimo.py`

- [x] T032 实现 DeepSeek fallback client
  - Files: `src/deepresearch/llm/deepseek.py`, `tests/llm/test_deepseek.py`
  - Done when: DeepSeek 通过统一 LLMClient 接口调用，真实调用测试打 `llm` marker。
  - Verify: `uv run pytest tests/llm/test_deepseek.py`

- [x] T033 实现 EmbeddingClient 抽象和 mock
  - Files: `src/deepresearch/embeddings/base.py`, `src/deepresearch/embeddings/mock.py`, `tests/embeddings/`
  - Done when: mock 输出 1024 维稳定向量。
  - Verify: `uv run pytest tests/embeddings`

- [x] T034 实现 OpenAI-compatible Qwen embedding client
  - Files: `src/deepresearch/embeddings/openai_compatible.py`, `tests/embeddings/test_openai_compatible.py`
  - Done when: 支持 batch size、timeout、retry、normalize=false 默认值。
  - Verify: `uv run pytest tests/embeddings/test_openai_compatible.py`

- [x] T035 实现 RerankerClient 抽象和 mock
  - Files: `src/deepresearch/rerankers/base.py`, `src/deepresearch/rerankers/mock.py`, `tests/rerankers/`
  - Done when: mock reranker 可稳定排序候选片段。
  - Verify: `uv run pytest tests/rerankers`

- [x] T036 实现 OpenAI-compatible bge reranker client
  - Files: `src/deepresearch/rerankers/openai_compatible.py`, `tests/rerankers/test_openai_compatible.py`
  - Done when: 支持 batch size、timeout、retry，真实调用测试打 `llm` marker。
  - Verify: `uv run pytest tests/rerankers/test_openai_compatible.py`

### M4 Retriever、正文抓取与切片

- [x] T040 实现 Retriever 抽象和 mock retriever
  - Files: `src/deepresearch/retrieval/base.py`, `tests/retrieval/test_base.py`
  - Done when: 统一返回 `RetrievedDocument`，错误结果可记录 trace。
  - Verify: `uv run pytest tests/retrieval/test_base.py`

- [x] T041 实现 LocalDatasetRetriever
  - Files: `src/deepresearch/retrieval/local_dataset.py`, `examples/corpus/`, `tests/retrieval/test_local_dataset.py`
  - Done when: 可读取 Markdown/JSONL 本地资料集并返回候选文档。
  - Verify: `uv run pytest tests/retrieval/test_local_dataset.py`

- [x] T042 实现 Tavily WebSearchProvider
  - Files: `src/deepresearch/retrieval/tavily_search.py`, `tests/retrieval/test_tavily_search.py`
  - Done when: 支持真实 Tavily 调用和 mock 响应；真实调用测试打 `network` marker。
  - Verify: `uv run pytest tests/retrieval/test_tavily_search.py`

- [x] T043 实现 MiMoSearchRetriever
  - Files: `src/deepresearch/retrieval/mimo_search.py`, `tests/retrieval/test_mimo_search.py`
  - Done when: 通过 MiMo `tools.web_search` 调用并转换为 `RetrievedDocument`；真实调用测试打 `llm`/`network` marker。
  - Verify: `uv run pytest tests/retrieval/test_mimo_search.py`

- [x] T044 实现网页正文抓取
  - Files: `src/deepresearch/retrieval/fetcher.py`, `tests/retrieval/test_fetcher.py`
  - Done when: 使用 `httpx + trafilatura` 抓取和清洗正文；失败返回可追踪错误，不阻塞主流程。
  - Verify: `uv run pytest tests/retrieval/test_fetcher.py`

- [x] T045 实现 chunking
  - Files: `src/deepresearch/retrieval/chunking.py`, `tests/retrieval/test_chunking.py`
  - Done when: 默认 1200 chars chunk、200 overlap、丢弃小于 300 chars 的碎片。
  - Verify: `uv run pytest tests/retrieval/test_chunking.py`

- [x] T046 实现 source_url + content_hash 去重
  - Files: `src/deepresearch/retrieval/dedup.py`, `tests/retrieval/test_dedup.py`
  - Done when: 相同 URL 和正文 hash 的 chunk 被去重。
  - Verify: `uv run pytest tests/retrieval/test_dedup.py`

### M5 Milvus MemoryStore

- [x] T050 实现 MemoryStore 抽象和 MockMemoryStore
  - Files: `src/deepresearch/memory/store.py`, `tests/memory/test_store.py`
  - Done when: mock 支持 upsert、search、delete、snapshot。
  - Verify: `uv run pytest tests/memory/test_store.py`

- [x] T051 实现 Milvus collection schema
  - Files: `src/deepresearch/memory/milvus_store.py`, `tests/memory/test_milvus_schema.py`
  - Done when: 创建 `deepresearch_chunks` 和 `deepresearch_memories`，向量字段 1024 维，COSINE + HNSW。
  - Verify: `uv run pytest tests/memory/test_milvus_schema.py`

- [x] T052 实现 Milvus upsert/search/delete
  - Files: `src/deepresearch/memory/milvus_store.py`, `tests/memory/test_milvus_store.py`
  - Done when: 支持按 `run_id`、`task_id`、`source_type`、`confidence` 过滤检索。
  - Verify: `uv run pytest -m milvus`

- [x] T053 实现 memory snapshot 导出
  - Files: `src/deepresearch/memory/milvus_store.py`, `tests/memory/test_snapshot.py`
  - Done when: 可导出 `outputs/<run_id>/memory_snapshot.jsonl`。
  - Verify: `uv run pytest tests/memory/test_snapshot.py`

### M6 DAG 与执行器

- [x] T060 实现 DAG 数据结构和无环校验
  - Files: `src/deepresearch/core/dag.py`, `tests/core/test_dag.py`
  - Done when: 支持依赖解析、ready task 查询、循环依赖报错。
  - Verify: `uv run pytest tests/core/test_dag.py`

- [x] T061 实现异步 DAG Executor 基础调度
  - Files: `src/deepresearch/core/executor.py`, `tests/core/test_executor.py`
  - Done when: 基于 `asyncio.Semaphore` 控制并发，按依赖执行任务。
  - Verify: `uv run pytest tests/core/test_executor.py`

- [x] T062 实现 timeout、retry 和 cancellation
  - Files: `src/deepresearch/core/executor.py`, `tests/core/test_executor_timeout.py`
  - Done when: 支持 task timeout、max retries、global timeout 和 cancelled 状态。
  - Verify: `uv run pytest tests/core/test_executor_timeout.py`

- [x] T063 实现 replan 和三级降级策略
  - Files: `src/deepresearch/core/executor.py`, `tests/core/test_replan.py`
  - Done when: 单任务失败、同层失败比例 >= 40%、evidence 为 0、information_insufficient 可触发 replan 或 limitation。
  - Verify: `uv run pytest tests/core/test_replan.py`

### M7 Agents 与报告生成

- [ ] T070 实现 Planner Agent
  - Files: `src/deepresearch/agents/planner.py`, `src/deepresearch/prompts/planner.md`, `tests/agents/test_planner.py`
  - Done when: 输入问题输出合法 DAG plan，使用 JSON fallback 和 Pydantic 校验。
  - Verify: `uv run pytest tests/agents/test_planner.py`

- [ ] T071 实现 Research Agent
  - Files: `src/deepresearch/agents/researcher.py`, `src/deepresearch/prompts/researcher.md`, `tests/agents/test_researcher.py`
  - Done when: 完成 query 生成、retriever 调用、fetch、chunk、embedding、Milvus 写入、rerank、evidence 抽取。
  - Verify: `uv run pytest tests/agents/test_researcher.py`

- [ ] T072 实现 Synthesizer
  - Files: `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/prompts/synthesizer.md`, `tests/agents/test_synthesizer.py`
  - Done when: 生成 Markdown 报告，关键 claim 使用 `[E12]` evidence id 引用，缺证内容进入 Limitations。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

### M8 Red-Blue 与 Evaluator

- [ ] T080 实现 Red Agent
  - Files: `src/deepresearch/agents/red_agent.py`, `src/deepresearch/prompts/red_agent.md`, `tests/agents/test_red_agent.py`
  - Done when: 输出事实性、逻辑一致性、引用质量、过度推断等结构化 issues。
  - Verify: `uv run pytest tests/agents/test_red_agent.py`

- [ ] T081 实现 Blue Agent
  - Files: `src/deepresearch/agents/blue_agent.py`, `src/deepresearch/prompts/blue_agent.md`, `tests/agents/test_blue_agent.py`
  - Done when: 支持 ADD、DELETE、MODIFY、VERIFY 修复动作。
  - Verify: `uv run pytest tests/agents/test_blue_agent.py`

- [ ] T082 实现 Judge 和 Red-Blue 终止条件
  - Files: `src/deepresearch/agents/judge.py`, `tests/agents/test_judge.py`
  - Done when: 支持 max_rounds=3、target_score=0.85、min_score_delta=0.03、oscillation_window=2。
  - Verify: `uv run pytest tests/agents/test_judge.py`

- [ ] T083 实现规则 Evaluator
  - Files: `src/deepresearch/evaluation/metrics.py`, `tests/evaluation/test_metrics.py`
  - Done when: 输出 task_success_rate、citation_coverage、empty_citation_rate、report_section_completeness、red_issue_count、blue_fix_count。
  - Verify: `uv run pytest tests/evaluation/test_metrics.py`

### M9 CLI、Run Manager 与 Smoke Demo

- [ ] T090 实现 RunManager
  - Files: `src/deepresearch/core/run_manager.py`, `tests/core/test_run_manager.py`
  - Done when: 创建 run_id，初始化 config、LLM、Retriever、Memory、Executor、TraceLogger，输出 run 目录。
  - Verify: `uv run pytest tests/core/test_run_manager.py`

- [ ] T091 实现 CLI 命令
  - Files: `src/deepresearch/cli.py`, `tests/test_cli.py`
  - Done when: 支持 `init`、`run`、`index-corpus`、`eval`、`inspect`、`config`。
  - Verify: `uv run pytest tests/test_cli.py` and `uv run deepresearch --help`

- [ ] T092 实现 mock 端到端 smoke run
  - Files: `tests/e2e/test_mock_run.py`, `examples/corpus/`
  - Done when: 无 API key、无互联网、无 Milvus Standalone 时可生成 report、trace、memory_snapshot、evaluation。
  - Verify: `uv run pytest tests/e2e/test_mock_run.py`

- [ ] T093 整理 README demo
  - Files: `README.md`
  - Done when: README 包含安装、配置、mock run、真实 run、测试命令和输出文件说明。
  - Verify: 文档人工检查。

## Done Summary

- [x] 确定 MVP 使用 Milvus Lite，后续迁移到 Docker Milvus Standalone。
- [x] 确定默认模型统一使用 MiMo v2.5 Pro，DeepSeek 作为 fallback。
- [x] 确定 embedding 使用 Qwen3-Embedding-4B 1024 维，reranker 使用 bge-reranker-v2-m32。
- [x] 确定真实 Web 搜索使用 Tavily，MVP 做轻量正文抓取。
- [x] 确定 chunk 参数为 1200 chars + 200 overlap，成本上限为每任务 5 query/20 doc/80 chunk。
- [x] 确定不使用 Agent 框架作为核心编排层。
- [x] 确定分支策略为 `main` 稳定分支、`develop` 日常开发分支。
- [x] 将当前开发分支切换到 `develop` 并准备初始提交。
- [x] 确定采用 `src/deepresearch/` 布局。
- [x] 确定默认测试离线可跑，联网和外部服务测试使用 marker。
- [x] 确定维护 `docs/TASKS.md` 和 `docs/WORKLOG.md`。

## Blocked

- [ ] 暂无。
