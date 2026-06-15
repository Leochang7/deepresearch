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
  - Done when: 支持 `--config`、`DEEPRESEARCH_CONFIG_PATH`、当前目录、用户目录、系统目录和内置默认值；配置值优先级为 CLI > file explicit values > env > default。
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

- [x] T070 实现 Planner Agent
  - Files: `src/deepresearch/agents/planner.py`, `src/deepresearch/prompts/planner.md`, `tests/agents/test_planner.py`
  - Done when: 输入问题输出合法 DAG plan，使用 JSON fallback 和 Pydantic 校验。
  - Verify: `uv run pytest tests/agents/test_planner.py`

- [x] T071 实现 Research Agent
  - Files: `src/deepresearch/agents/researcher.py`, `src/deepresearch/prompts/researcher.md`, `tests/agents/test_researcher.py`
  - Done when: 完成 query 生成、retriever 调用、fetch、chunk、embedding、Milvus 写入、rerank、evidence 抽取。
  - Verify: `uv run pytest tests/agents/test_researcher.py`

- [x] T072 实现 Synthesizer
  - Files: `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/prompts/synthesizer.md`, `tests/agents/test_synthesizer.py`
  - Done when: 生成 Markdown 报告，关键 claim 使用 `[E12]` evidence id 引用，缺证内容进入 Limitations。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

### M8 Red-Blue 与 Evaluator

- [x] T080 实现 Red Agent
  - Files: `src/deepresearch/agents/red_agent.py`, `src/deepresearch/prompts/red_agent.md`, `tests/agents/test_red_agent.py`
  - Done when: 输出事实性、逻辑一致性、引用质量、过度推断等结构化 issues。
  - Verify: `uv run pytest tests/agents/test_red_agent.py`

- [x] T081 实现 Blue Agent
  - Files: `src/deepresearch/agents/blue_agent.py`, `src/deepresearch/prompts/blue_agent.md`, `tests/agents/test_blue_agent.py`
  - Done when: 支持 ADD、DELETE、MODIFY、VERIFY 修复动作。
  - Verify: `uv run pytest tests/agents/test_blue_agent.py`

- [x] T082 实现 Judge 和 Red-Blue 终止条件
  - Files: `src/deepresearch/agents/judge.py`, `tests/agents/test_judge.py`
  - Done when: 支持 max_rounds=3、target_score=0.85、min_score_delta=0.03、oscillation_window=2。
  - Verify: `uv run pytest tests/agents/test_judge.py`

- [x] T083 实现规则 Evaluator
  - Files: `src/deepresearch/evaluation/metrics.py`, `tests/evaluation/test_metrics.py`
  - Done when: 输出 task_success_rate、citation_coverage、empty_citation_rate、report_section_completeness、red_issue_count、blue_fix_count。
  - Verify: `uv run pytest tests/evaluation/test_metrics.py`

### M9 CLI、Run Manager 与 Smoke Demo

- [x] T090 实现 RunManager
  - Files: `src/deepresearch/core/run_manager.py`, `tests/core/test_run_manager.py`
  - Done when: 创建 run_id，初始化 config、LLM、Retriever、Memory、Executor、TraceLogger，输出 run 目录。
  - Verify: `uv run pytest tests/core/test_run_manager.py`

- [x] T091 实现 CLI 命令
  - Files: `src/deepresearch/cli.py`, `tests/test_cli.py`
  - Done when: 支持 `init`、`run`、`index-corpus`、`eval`、`inspect`、`config`。
  - Verify: `uv run pytest tests/test_cli.py` and `uv run deepresearch --help`

- [x] T092 实现 mock 端到端 smoke run
  - Files: `tests/e2e/test_mock_run.py`, `examples/corpus/`
  - Done when: 无 API key、无互联网、无 Milvus Standalone 时可生成 report、trace、memory_snapshot、evaluation。
  - Verify: `uv run pytest tests/e2e/test_mock_run.py`

- [x] T093 整理 README demo
  - Files: `README.md`
  - Done when: README 包含安装、配置、mock run、真实 run、测试命令和输出文件说明。
  - Verify: 文档人工检查。

### MVP 真实环境验收

- [x] T094 修复真实检索运行的超时与 Milvus Standalone 接入问题
  - Files: `src/deepresearch/agents/researcher.py`, `src/deepresearch/core/run_manager.py`, `src/deepresearch/memory/milvus_store.py`, `src/deepresearch/retrieval/tavily_search.py`, tests
  - Done when: Tavily query 和正文抓取支持有界并发，Research Agent 使用配置中的 query/doc/chunk 限额，默认连接 Docker Milvus Standalone，trace 可定位研究阶段；真实模式全部任务失败时 CLI 返回非 0。
  - Verify: `uv run pytest`, `uv run ruff check .`, 真实 Tavily smoke run `outputs/real-tavily-standalone-ok-smoke`。

- [x] T095 修复报告 References 缺少 URL 的引用质量问题
  - Files: `src/deepresearch/agents/synthesizer.py`, `tests/agents/test_synthesizer.py`
  - Done when: Evidence 中存在 `source_url` 时 References 输出 `标题 - URL`，传给 Synthesizer 的 evidence context 显式包含 Source URL。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py tests/core/test_run_manager.py tests/e2e/test_mock_run.py tests/evaluation/test_metrics.py`

- [x] T096 清理 Milvus Lite / 本地文件型 Milvus 测试残留
  - Files: `src/deepresearch/memory/milvus_store.py`, `tests/memory/test_milvus_store.py`, `tests/memory/test_milvus_schema.py`
  - Done when: MilvusStore 默认只按 Standalone URI 连接，不再测试本地 `.db` 父目录创建逻辑。
  - Verify: `uv run pytest tests/memory/test_milvus_store.py tests/memory/test_milvus_schema.py`

## Done Summary

- [x] 确定 MVP 直接使用 Docker Milvus Standalone。
- [x] 确定默认模型统一使用 MiMo v2.5 Pro，DeepSeek 作为 fallback。
- [x] 确定真实验收环境 embedding 使用 Qwen3-Embedding-4B 2560 维，reranker 使用 bge-reranker-v2-m3。
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

## Post-MVP Backlog

### PM0 真实环境自检与工程可靠性

- [x] PM001 实现 `deepresearch doctor`
  - Files: `src/deepresearch/cli.py`, `src/deepresearch/doctor.py`, `tests/test_doctor.py`, `pyproject.toml`
  - Done when: 可检查必需环境变量、MiMo/Tavily/embedding/reranker endpoint、模型列表、embedding 维度、reranker 模型、Milvus Standalone 连接和 collection schema；不打印密钥值。
  - Verify: `uv run pytest tests/test_doctor.py`; real mode uses `uv run deepresearch doctor --real`

- [x] PM002 增加真实模式 integration/e2e 测试入口
  - Files: `tests/integration/`, `pyproject.toml`
  - Done when: Tavily、MiMo、embedding、reranker、Milvus Standalone smoke tests 使用 `integration/network/milvus/llm` marker；默认 `uv run pytest` 仍离线可跑；真实调用必须显式设置 `DEEPRESEARCH_RUN_REAL_INTEGRATION=1`。
  - Verify: `uv run pytest`, `uv run pytest -m integration`

- [x] PM003 迁移 Milvus ORM API 到 `MilvusClient`
  - Files: `src/deepresearch/memory/milvus_store.py`, `tests/memory/`
  - Done when: 真实运行不再输出 PyMilvus ORM deprecation warning，collection init/upsert/search/snapshot 行为保持一致。
  - Verify: `uv run pytest tests/memory`

### PM1 检索质量增强

- [x] PM010 实现 document-level RRF
  - Files: `src/deepresearch/retrieval/fusion.py`, `tests/retrieval/test_fusion.py`
  - Done when: 支持多个 ranked `RetrievedDocument` 列表融合，默认 `rrf_k=60`、`max_fused_results=20`，按 canonical URL 或 `title + content_hash` 去重。
  - Verify: `uv run pytest tests/retrieval/test_fusion.py`

- [x] PM011 将 RRF 接入多 query 搜索结果
  - Files: `src/deepresearch/retrieval/fusion.py`, `src/deepresearch/agents/researcher.py`
  - Done when: 多 query 返回的候选文档先 RRF 融合，再进入 fetch/chunk；trace 记录融合前后数量。
  - Verify: `uv run pytest tests/agents/test_researcher.py tests/retrieval`

- [x] PM012 实现 chunk-level RRF 设计与第一版
  - Files: `src/deepresearch/retrieval/fusion.py`, `src/deepresearch/agents/researcher.py`, `src/deepresearch/memory/store.py`, `src/deepresearch/memory/milvus_store.py`, tests
  - Done when: Milvus 多 query vector recall 与独立关键词 recall 可融合后再 rerank。
  - Verify: `uv run pytest tests/agents/test_researcher.py`

- [x] PM013 实现 chunk-level MMR context selection
  - Files: `src/deepresearch/retrieval/fusion.py`, `src/deepresearch/agents/researcher.py`, `tests/retrieval/test_fusion.py`
  - Done when: RRF/rerank 后的候选 chunks 支持按 `mmr_lambda=0.7` 做相关性与多样性选择，默认最多保留 12 个 context chunks。
  - Verify: `uv run pytest tests/retrieval/test_fusion.py tests/agents/test_researcher.py`

### PM2 引用与证据质量

- [x] PM020 增强 References 输出
  - Files: `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/agents/researcher.py`, `src/deepresearch/schemas/evidence.py`, `tests/agents/test_synthesizer.py`
  - Done when: References 去重，输出 `title + url + retrieved_at`，缺失 URL 时明确标记 local source。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

- [x] PM021 Red Agent 增加引用支持度检查
  - Files: `src/deepresearch/agents/red_agent.py`, `src/deepresearch/prompts/red_agent.md`, tests
  - Done when: Red Agent 能输出“引用不能支持 claim”的结构化 issue。
  - Verify: `uv run pytest tests/agents/test_red_agent.py`

- [x] PM022 增加 evidence 质量门控
  - Files: `src/deepresearch/agents/evidence_quality.py`, `src/deepresearch/agents/researcher.py`, `src/deepresearch/schemas/evidence.py`, tests
  - Done when: quote 必须原文命中，低置信 evidence 不进入 synthesis，claim/quote 语义一致性检查有可替换接口。
  - Verify: `uv run pytest tests/agents/test_researcher.py`

- [x] PM023 增加 report profile
  - Files: `src/deepresearch/agents/report_profiles.py`, `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/config.py`, `.env.example`, `docs/CONFIGURATION.md`, tests
  - Done when: 支持 `factual_answer`、`comparison`、`timeline`、`tech_research`、`risk_analysis` 报告模板。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

### PM3 Replan 与预算控制

- [x] PM030 实现真实 replan 闭环
  - Files: `src/deepresearch/core/executor.py`, `src/deepresearch/agents/planner.py`, tests
  - Done when: task 失败、evidence 为 0、同层失败率过高时可生成无冲突 ID 的替代 task；受影响的 skipped/cancelled 下游任务按新依赖恢复执行；原任务标记为 `REPLANNING` 历史态且不计入成功率；所有 replan 共享 run 级全局超时；trace 记录来源、替代任务和被替换任务。
  - Verify: `uv run pytest tests/core/test_replan.py tests/core/test_executor.py tests/core/test_run_manager.py`

- [x] PM031 增加 run budget 统计
  - Files: `src/deepresearch/core/run_manager.py`, `src/deepresearch/core/trace.py`, schemas/tests
  - Done when: 通过统一 client wrapper 按真实调用记录 LLM/search/embedding/rerank 次数和 token usage，同时记录 fetched docs、chunks、elapsed time；`max_llm_calls_per_run` 在调用前强制执行；预算写入 trace 和 `evaluation.json`。
  - Verify: `uv run pytest tests/core/test_budget.py tests/core/test_run_manager.py`

### PM4 Trace 与展示

- [ ] PM040 增强 `inspect --timeline`
  - Files: `src/deepresearch/cli.py`, tests/docs
  - Done when: CLI 可按 task 输出阶段耗时、失败原因、query/doc/chunk/evidence 数量。
  - Verify: `uv run pytest tests/test_cli.py`

- [ ] PM041 增加 MVP 验收文档
  - Files: `docs/MVP_ACCEPTANCE.md`, `README.md`
  - Done when: 记录真实 smoke run 配置、指标、产物路径、已知限制和复现命令。
  - Verify: 文档人工检查。

### PM5 Memory 与数据治理

- [ ] PM050 增加 Memory schema version
  - Files: `src/deepresearch/memory/milvus_store.py`, config/docs/tests
  - Done when: collection metadata 记录 embedding model、dim、schema version，启动时校验配置匹配。
  - Verify: `uv run pytest tests/memory`

- [ ] PM051 增加轻量冲突检测
  - Files: `src/deepresearch/memory/conflict.py`, tests
  - Done when: 支持同实体不同日期/数值、相反结论词、同 source_url 不同 claim 的启发式检测。
  - Verify: `uv run pytest tests/memory/test_conflict.py`

### PM6 评测与实验

- [ ] PM060 固化真实 smoke question set
  - Files: `examples/questions.txt`, `tests/e2e/`, `docs/MVP_ACCEPTANCE.md`
  - Done when: 有 3-5 个固定真实问题和对应指标记录。
  - Verify: `uv run pytest tests/e2e`

- [ ] PM061 设计 ResearchBench mini
  - Files: `src/deepresearch/evaluation/benchmark.py`, `docs/`
  - Done when: 支持少量多领域问题、规则指标汇总和 JSONL 输出。
  - Verify: `uv run pytest tests/evaluation`
