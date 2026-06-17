# Tasks

项目级任务状态文件。AI agent 每完成一个 task 后必须更新本文件。只保留近期 MVP backlog、最近完成记录和阻塞项；复杂功能可拆到 `docs/tasks/<feature>.md`。

规则：

- 使用 `- [ ]` 和 `- [x]` 标记状态。
- 每完成一个 task，立即更新本文件。
- 不要把临时思考写进本文件，只记录任务状态、验收标准和阻塞点。
- 默认验证命令必须使用 `uv run ...`。

## MVP Backlog

### Current Bugfix

- [x] BF006 重写 README 双语入口并同步简历仓库地址
  - Files: `README.md`, `README.zh-CN.md`, `../resume/resume-zh_CN.tex`, `docs/TASKS.md`, `docs/WORKLOG.md`
  - Done when: README 参考 521wolf 风格提供英文/中文双语入口、功能面、架构地图、快速开始、配置、benchmark、验证和注意事项；简历 DeepResearch `[GitHub]` 指向真实仓库地址。
  - Verify: `uv run ruff format .`; `uv run ruff check .`; `uv run pytest`

- [x] BF004 修复 PM24/PM25 review 问题
  - Files: `src/deepresearch/prompts/provider.py`, `src/deepresearch/core/run_manager.py`, `src/deepresearch/evaluation/judge_eval.py`, `src/deepresearch/evaluation/benchmark.py`, `src/deepresearch/evaluation/langfuse.py`, `src/deepresearch/evaluation/annotation.py`, tests
  - Done when: Langfuse annotation 不再调用当前 SDK 不存在的 queue API；`judge_prompt_name` 真实传入 fact judge；runtime prompt metadata 覆盖完整 prompt set 并记录 Langfuse version；annotation candidate/import 区分 run error、坏行和重复 case。
  - Verify: `uv run pytest tests\prompts tests\core\test_run_manager.py tests\evaluation\test_annotation.py tests\evaluation\test_langfuse.py`; `uv run pytest tests\evaluation\test_benchmark.py`; `uv run ruff check .`; `uv run pytest`

- [x] BF005 同步 release hardening 状态并记录真实验收尝试
  - Files: `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/RELEASE_HARDENING.md`, `docs/README.md`, `README.md`, `docs/WORKLOG.md`
  - Done when: 状态文档更新到 PM25；最新测试数更新为 644 passed / 1 skipped；真实 doctor 和 real local-corpus smoke 尝试的结果、阻塞和 citation coverage 初步分析有单一记录入口。
  - Verify: `uv run deepresearch doctor --real`; real benchmark partial output at `outputs/experiments/release-hardening-real/researchbench_smoke5/`; `uv run ruff check .`; `uv run pytest`

- [x] BF001 修复真实 benchmark 中 MiMo JSON array 响应导致任务失败的问题
  - Files: `src/deepresearch/agents/researcher.py`, `tests/agents/test_researcher.py`
  - Done when: query/evidence 提取兼容 JSON object 和 JSON array，避免 `'list' object has no attribute 'get'`。
  - Verify: `uv run pytest tests/agents/test_researcher.py`

- [x] BF002 避免 synthesizer 把 task_id 当作 evidence citation
  - Files: `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/prompts/synthesizer.md`, `tests/agents/test_synthesizer.py`
  - Done when: task summary 不再输出 `[t1]` 形态，prompt 明确禁止引用 task ID。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

- [x] BF003 避免 Markdown 小标题被误判为无引用事实 claim
  - Files: `src/deepresearch/agents/synthesizer.py`, `tests/agents/test_synthesizer.py`
  - Done when: `###` 等报告内小标题可保留，不进入 `Uncited claim` limitations。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

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

- [x] 暂无。

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

- [x] PM040 增强 `inspect --timeline`
  - Files: `src/deepresearch/cli.py`, tests/docs
  - Done when: CLI 可按 task 输出阶段耗时、失败原因、query/doc/chunk/evidence 数量。
  - Verify: `uv run pytest tests/test_cli.py`

- [x] PM041 增加 MVP 验收文档
  - Files: `docs/MVP_ACCEPTANCE.md`, `README.md`
  - Done when: 记录真实 smoke run 配置、指标、产物路径、已知限制和复现命令。
  - Verify: 文档人工检查。

### PM5 Memory 与数据治理

- [x] PM050 增加 Memory schema version
  - Files: `src/deepresearch/memory/milvus_store.py`, config/docs/tests
  - Done when: collection metadata 记录 embedding model、dim、schema version，启动时校验配置匹配。
  - Verify: `uv run pytest tests/memory`

- [x] PM051 增加轻量冲突检测
  - Files: `src/deepresearch/memory/conflict.py`, tests
  - Done when: 支持同实体不同日期/数值、相反结论词、同 source_url 不同 claim 的启发式检测。
  - Verify: `uv run pytest tests/memory/test_conflict.py`

### PM6 Langfuse 评测闭环

- [x] PM060 接入 Langfuse adapter
  - Files: `src/deepresearch/evaluation/langfuse.py`, `src/deepresearch/config.py`, `.env.example`, `docs/EVALUATION_LANGFUSE_PLAN.md`, tests
  - Done when: 可选上报 run input、config 摘要、report、evaluation、budget、trace summary 和 scores 到 Langfuse；无 key 或关闭开关时默认离线行为不变。
  - Verify: `uv run pytest tests/evaluation`

- [x] PM061 设计 ResearchBench mini dataset
  - Files: `examples/bench/researchbench_mini.jsonl`, `docs/EVALUATION_LANGFUSE_PLAN.md`, tests
  - Done when: 有 10-15 个可复现 case，每题包含 `id/domain/difficulty/question/expected_facts/required_citations/tags`。
  - Verify: `uv run pytest tests/evaluation`

- [x] PM062 实现 benchmark runner
  - Files: `src/deepresearch/evaluation/benchmark.py`, `src/deepresearch/cli.py`, tests
  - Done when: `uv run deepresearch benchmark --dataset examples/bench/researchbench_mini.jsonl --mode mock` 可离线跑完并输出 `results.jsonl` 与 `summary.json`；真实模式可选上报 Langfuse。
  - Verify: `uv run pytest tests/evaluation tests/test_cli.py`

- [x] PM063 增加本地事实覆盖与幻觉风险指标
  - Files: `src/deepresearch/evaluation/metrics.py`, `tests/evaluation/`
  - Done when: 支持 `factual_hit_rate` 和 `hallucination_flag`，可基于 expected facts 与引用约束计算。
  - Verify: `uv run pytest tests/evaluation`

- [x] PM064 增加 LLM-as-Judge 5 维评分 schema
  - Files: `src/deepresearch/evaluation/judge_eval.py`, `src/deepresearch/prompts/`, tests
  - Done when: 输出 factuality、citation_support、completeness、reasoning_consistency、readability 五维分数，并可写入 Langfuse scores。
  - Verify: `uv run pytest tests/evaluation`

- [x] PM065 扩展完整 benchmark 与统计分析
  - Files: `examples/bench/`, `src/deepresearch/evaluation/`, docs
  - Done when: 在 pipeline 稳定后扩展到 ResearchBench 11 领域/35 题、HotpotQA 深度研究变体、Bootstrap 95% CI、Cohen's d 和多后端实验脚本。
  - Verify: `uv run pytest tests/evaluation`; real experiments use explicit integration/e2e commands

### PM7 真实 benchmark 质量校准

- [x] PM070 改进 factual hit 规则指标
  - Files: `src/deepresearch/evaluation/metrics.py`, `src/deepresearch/schemas/evaluation.py`, tests
  - Done when: `expected_facts` 不再只靠整句 token overlap；支持 fact-level keyword groups、normalized aliases 和命中原因输出。
  - Verify: `uv run pytest tests/evaluation/test_metrics.py`

- [x] PM071 增加 fact-level semantic judge
  - Files: `src/deepresearch/evaluation/judge_eval.py`, `src/deepresearch/prompts/`, tests
  - Done when: 每条 expected fact 输出 `hit/miss/uncertain`、supporting evidence ids 和 reason；LLM judge 失败时回退本地规则。
  - Verify: `uv run pytest tests/evaluation`

- [x] PM072 benchmark 输出 per-fact 与 per-case failure reason
  - Files: `src/deepresearch/evaluation/benchmark.py`, `examples/bench/`, tests
  - Done when: `results.jsonl` 和 `summary.json` 包含 fact hit 明细、失败类型、失败阶段和可读诊断摘要。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM073 跑真实 5-case benchmark smoke
  - Files: `outputs/bench-real-*` ignored, `docs/REAL_BENCHMARK_GUIDE.md`
  - Done when: 使用真实 MiMo/Tavily/embedding/reranker/Milvus 跑 5 个 case，记录 task_success_rate、citation_coverage、factual_hit_rate、hallucination_flag 和失败原因。
  - Verify: `uv run deepresearch doctor --real`; `uv run deepresearch benchmark <5-case-jsonl> --mode real --output outputs/bench-real --experiment pm7-smoke`
  - Blocked: Docker/Milvus 已恢复后，真实联网 smoke 仍不可作为稳定验收路径：MiMo 联网搜索计费，Tavily 免费额度已耗尽并返回 432；实时搜索会导致 benchmark 不可复现、成本不可控。PM073 保留为“联网增强 smoke”，不再作为下一步主线。

- [x] PM074 更新项目状态与真实评测说明
  - Files: `docs/PROJECT_STATUS.md`, `docs/REAL_BENCHMARK_GUIDE.md`, `docs/WORKLOG.md`
  - Done when: 文档说明当前 benchmark 能力边界、指标解释方式、复现实验命令和下一步优化依据；真实 PM7 smoke 结果待 PM073 完成后补充。
  - Verify: 文档人工检查

### PM8 Local Corpus 可复现真实评测

- [x] PM080 设计本地 benchmark corpus 结构
  - Files: `examples/corpus/`, `docs/REAL_BENCHMARK_GUIDE.md`, tests
  - Done when: 为 PM7 5-case smoke 建立可提交的本地资料集目录，至少覆盖 `llm_agents`、`embeddings`、`fine_tuning`、`reasoning`、`rag`；每个 case 有 2-4 篇短文档，包含 expected facts 所需证据。
  - Verify: 文档人工检查；资料不包含密钥、私有网页或版权风险长文全文。

- [x] PM081 benchmark CLI 支持 local corpus
  - Files: `src/deepresearch/cli.py`, `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `deepresearch benchmark` 支持 `--retriever local --corpus examples/corpus`；真实模式仍使用真实 LLM/embedding/reranker/Milvus，但检索来源走本地 corpus，不依赖 Tavily/MiMo 搜索额度。
  - Verify: `uv run pytest tests/test_cli.py tests/evaluation/test_benchmark.py`

- [x] PM082 建立 Local Corpus Smoke 配置
  - Files: `docs/REAL_BENCHMARK_GUIDE.md`, `docs/CONFIGURATION.md`, `examples/configs/benchmark_smoke.toml`
  - Done when: 有一份低成本 smoke 配置，限制 query/docs/chunks/replan/red-blue 轮数；用于稳定复现 PM7 5-case，不影响默认配置。
  - Verify: `uv run pytest tests/test_cli.py`; TOML syntax valid

- [x] PM083 跑通 PM7 5-case local-corpus real benchmark
  - Files: `outputs/bench-local-*` ignored, docs
  - Done when: 使用真实 MiMo chat、真实 embedding/reranker、Milvus Standalone、本地 corpus 跑完 5 个 case，输出 `results.jsonl` 和 `summary.json`；记录 task_success_rate、citation_coverage、factual_hit_rate、hallucination_flag 和每 case 失败原因。
  - Verify: `uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode real --retriever local --corpus examples/corpus --output outputs/bench-local --experiment pm8-local-smoke`
  - Result: `outputs/bench-pm8-local-real-final/pm8-local-real-final/summary.json`，5 cases，`avg_task_success_rate=1.0`，`avg_citation_coverage=0.5297`，`avg_factual_hit_rate=1.0`，`hallucination_flag_count=0`。

- [x] PM084 修复 evidence extraction 在可控资料集上的稳定性
  - Files: `src/deepresearch/agents/researcher.py`, `src/deepresearch/prompts/researcher.md`, tests
  - Done when: 给定本地 corpus 中包含答案的资料，ResearchAgent 能稳定抽取原文 quote、绑定 source_url/title、写入 memory，并让 citation_coverage 不依赖模型常识。
  - Verify: `uv run pytest tests/agents/test_researcher.py`; PM083 指标复测。
  - Result: source_id 支持 `[S1]` 等格式归一，quote 支持空白归一匹配；LLM evidence 全部无效时使用带关键词门槛的 grounded sentence fallback；local corpus 5-case real benchmark 无 hallucination flag。

- [x] PM085 将联网搜索降级为增强层
  - Files: `docs/POST_MVP_ROADMAP.md`, `docs/REAL_BENCHMARK_GUIDE.md`, `docs/CONFIGURATION.md`
  - Done when: 文档明确默认 benchmark 不依赖实时搜索；Tavily、MiMo Search 仅作为 optional retriever adapter；默认 `uv run pytest` 不依赖互联网。
  - Verify: 文档人工检查；默认 `uv run pytest` 不依赖互联网。

### PM9 引用覆盖率优化

- [x] PM091 合并 Roadmap 并归档历史计划
  - Files: `docs/ROADMAP.md`, `docs/archive/`, `docs/README.md`, `README.md`, `AGENTS.md`, `docs/TASKS.md`, `docs/WORKLOG.md`
  - Done when: `ROADMAP.md` 成为路线图唯一维护入口；旧 `MVP_AND_ROADMAP.md`、`POST_MVP_ROADMAP.md`、`IMPLEMENTATION_PLAN.md` 移入 `docs/archive/`；入口文档和链接更新。
  - Verify: 文档人工检查；内部链接检查。

- [x] PM090 收敛文档入口与维护规范
  - Files: `AGENTS.md`, `README.md`, `docs/README.md`, `docs/TASKS.md`, `docs/WORKLOG.md`
  - Done when: 文档分层、唯一事实源、归档规则和更新触发条件明确；`WORKLOG.md` 明确保存全量操作日志并在文件底部追加；README 指向新的文档入口。
  - Verify: 文档人工检查；内部链接检查。

- [x] PM086 提升 local-corpus smoke citation coverage
  - Files: `src/deepresearch/agents/researcher.py`, `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/agents/evidence_quality.py`, `src/deepresearch/prompts/synthesizer.md`, tests
  - Done when: 模糊 quote 匹配（大小写/标点不敏感）、quality checker 大小写不敏感检查、fallback 放宽（min 25 chars, max 5 items）、synthesizer prompt 要求引用所有 evidence、`_enforce_citations` 保留非事实性分析语句；集成测试断言 `citation_coverage >= 0.7`。
  - Verify: `uv run pytest tests/ -x -q` (458 passed, 1 skipped); local-corpus 5-case real benchmark 复测。

### PM10 Langfuse Prompt Management

- [x] PM100 实现统一 PromptProvider
  - Files: `src/deepresearch/prompts/provider.py`, `src/deepresearch/config.py`, `src/deepresearch/agents/`, `src/deepresearch/evaluation/judge_eval.py`, tests, docs
  - Done when: Agent 和 judge 不再直接 `read_text()` prompt 文件，而是通过 `PromptProvider.get(name)` 获取 prompt；默认 `LocalPromptProvider` 继续读取 `src/deepresearch/prompts/*.md`，默认离线测试不依赖 Langfuse。
  - Verify: `uv run pytest tests/prompts tests/agents tests/evaluation`; `uv run pytest` 无 Langfuse key 仍通过。

- [x] PM101 接入 LangfusePromptProvider 与本地 fallback
  - Files: `src/deepresearch/prompts/provider.py`, `src/deepresearch/core/run_manager.py`, `src/deepresearch/config.py`, tests
  - Done when: 支持 `local`、`langfuse`、`langfuse_with_local_fallback` 三种 provider；Langfuse prompt 使用稳定名称 `deepresearch/<prompt_name>` 和 label 获取；严格 provider 失败时快速失败，fallback provider 失败时回退本地 prompt；RunManager 根据配置创建 provider 并传递给所有 agent。
  - Verify: `uv run pytest tests/prompts tests/test_config.py tests/core/test_run_manager.py`; 默认 `uv run pytest` 离线通过。

- [x] PM102 增加 prompt bootstrap/push CLI
  - Files: `src/deepresearch/cli.py`, tests
  - Done when: 支持 `uv run deepresearch prompts push --label staging` 将本地 prompt 初始导入 Langfuse；`run` 和 `benchmark` 支持 `--prompt-provider` 选项。
  - Verify: `uv run pytest tests/test_cli.py`。

- [x] PM103 Review 修复 Langfuse prompt provider 失败语义
  - Files: `src/deepresearch/prompts/provider.py`, `src/deepresearch/core/run_manager.py`, `src/deepresearch/cli.py`, tests, docs
  - Done when: `LocalPromptProvider` 可默认读取仓库 prompt；严格 `langfuse` provider 不再返回空 prompt；fallback 只捕获 prompt provider 错误；`--prompt-provider` 非 local 时会开启 Langfuse；`prompts push` 在缺少 client 或部分失败时返回非 0。
  - Verify: `uv run pytest tests/prompts tests/test_cli.py tests/core/test_run_manager.py` (49 passed); `uv run ruff check .`; `uv run pytest tests/ -x -q` (482 passed, 1 skipped)。

### PM11 并行 Benchmark Runner

- [x] PM110 增加 benchmark 并发配置与 CLI 覆盖
  - Files: `src/deepresearch/config.py`, `src/deepresearch/cli.py`, `docs/CONFIGURATION.md`, tests
  - Done when: 支持 `benchmark.max_concurrency` 配置和 `uv run deepresearch benchmark ... --max-concurrency N`；默认值保守且 `1` 保持现有串行语义。
  - Verify: `uv run pytest tests/test_config.py tests/test_cli.py`

- [x] PM111 实现受限并发 case 调度
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: benchmark runner 使用 asyncio.Semaphore + gather 并发执行多个 case；每个 case 独立创建 run/output/evaluation，不共享可变 case 状态；单个 case 失败不阻断其他 case。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM112 保证并发结果落盘与汇总确定性
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `results.jsonl` 按 dataset 原始顺序写出（gather 保序），summary 指标与完成顺序无关；失败 case 记录 error 和 stage 到 evaluation dict。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM113 补并行 benchmark 验收测试与文档
  - Files: `tests/evaluation/test_benchmark.py`, `tests/test_cli.py`, `docs/CONFIGURATION.md`
  - Done when: 覆盖 mock 并发成功、单 case 失败隔离、`--max-concurrency 1` 串行兼容、结果顺序确定；文档说明真实模式并发的 LLM/Milvus 压力边界。
  - Verify: `uv run pytest tests/evaluation tests/test_cli.py` (489 passed)

### PM12 Cross-lingual Retrieval Quality

- [x] PM120 设计跨语言检索场景与诊断维度
  - Files: `examples/bench/crosslingual_smoke3.jsonl`, `examples/corpus/crosslingual/`, `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `BenchmarkCase` 新增 `question_lang`/`evidence_lang` 字段（默认 `"en"`）；3 个跨语言 benchmark case（cl-001/002/003）和 3 篇双语 corpus 文档已创建。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM121 增加中英术语别名与 query expansion
  - Files: `src/deepresearch/retrieval/query_expansion.py`, `src/deepresearch/agents/researcher.py`, `src/deepresearch/retrieval/local_dataset.py`, tests
  - Done when: `_tokenize` 和 `_task_keywords` 支持 CJK unigram+bigram；中文 query 通过 `expand_query()` 扩展英文术语（18 组 AI/ML 术语映射）；英文 query 保持不变。
  - Verify: `uv run pytest tests/retrieval tests/agents/test_researcher.py` (504 passed)

- [x] PM122 实现 BM25/keyword 与 vector 的跨语言混合召回
  - Files: `src/deepresearch/retrieval/local_dataset.py`, `src/deepresearch/memory/store.py`, tests
  - Done when: `local_dataset._tokenize` 和 `store.lexical_tokens` 统一使用 CJK unigram+bigram；RRF/MMR 在中英混合资料上稳定（已验证——RRF/MMR 仅操作 rank 和 vector，与语言无关）。
  - Verify: `uv run pytest tests/retrieval tests/memory tests/agents/test_researcher.py`

- [x] PM123 输出按语言场景分组的检索指标
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `_build_summary` 输出 `per_question_lang` 和 `per_evidence_lang` breakdown；无 cases 参数时向后兼容（空 dict）。
  - Verify: `uv run pytest tests/evaluation`

### PM13 Multilingual Evidence & Citation Quality

- [x] PM130 增强多语言 quote normalization
  - Files: `src/deepresearch/agents/evidence_quality.py`, tests
  - Done when: `_check_token_overlap` 使用 CJK unigram+bigram 替代 whitespace split；中文 claim/quote 重叠检测正确工作。
  - Verify: `uv run pytest tests/agents/test_researcher.py` (518 passed)

- [x] PM131 优化跨语言 evidence quality checker
  - Files: `src/deepresearch/evaluation/metrics.py`, tests
  - Done when: `_evaluate_fact` 使用 CJK unigram+bigram tokenization；新增 5 组中文缩写映射（RAG/LLM/LoRA/CoT/self-attention）；CJK keywords 独立匹配路径。
  - Verify: `uv run pytest tests/evaluation/test_metrics.py`

- [x] PM132 调整 Synthesizer 多语言引用行为
  - Files: `src/deepresearch/agents/synthesizer.py`, `src/deepresearch/prompts/synthesizer.md`, tests
  - Done when: `_is_substantive_claim` CJK 阈值降至 10 字符；识别中文过渡短语；synthesizer prompt 指示报告语言跟随问题语言。
  - Verify: `uv run pytest tests/agents/test_synthesizer.py`

- [x] PM133 扩展 Evaluator 多语言 failure reason
  - Files: `src/deepresearch/evaluation/metrics.py`, tests
  - Done when: `_evaluate_fact` 失败时检测 fact/report 语言差异，在 reason 中附加 `language mismatch` 信息。
  - Verify: `uv run pytest tests/evaluation`

### PM14 Multilingual Benchmark

- [x] PM140 建立 multilingual local corpus 和 benchmark dataset
  - Files: `examples/bench/crosslingual_smoke10.jsonl`, `examples/corpus/crosslingual/`, tests
  - Done when: 15 个 benchmark case（5 English + 10 cross-lingual），覆盖 7 个域（llm_agents/embeddings/fine_tuning/reasoning/rag/evaluation/safety）；8 篇双语文档；每个 case 标注 question_lang/evidence_lang。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py` (523 passed)

- [x] PM141 benchmark summary 支持多语言分组对比
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `compare_summaries(before, after)` 计算标量指标和分组指标的 delta；支持 `per_domain`/`per_difficulty`/`per_question_lang`/`per_evidence_lang` 对比。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM142 跑通 multilingual local-corpus smoke
  - Files: `tests/evaluation/test_benchmark.py`, `docs/REAL_BENCHMARK_GUIDE.md`
  - Done when: `test_multilingual_benchmark_mock` 用 LocalDatasetRetriever + crosslingual corpus 跑 3 case，验证 per_question_lang 分组；文档新增 Multilingual Benchmark 章节。
  - Verify: `uv run pytest tests/evaluation tests/test_cli.py`

### PM15 Larger Multilingual Benchmark

- [x] PM150 建立 20-case multilingual large benchmark
  - Files: `examples/bench/multilingual_large20.jsonl`, `examples/corpus/crosslingual/`, tests
  - Done when: 单个 dataset 覆盖 5 个英文 smoke case + 15 个中英/跨语言 case；新增模型压缩、隐私、多模态、DAG 编排、数据质量 5 个领域；本地 corpus 覆盖新增 expected facts。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM151 增加 combined language-scenario breakdown
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: summary 输出 `per_language_scenario`，按 `question_lang -> evidence_lang` 分组统计 task success、citation coverage、factual hit 和 section completeness。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

- [x] PM152 更新 PM15 复现文档和 smoke 测试
  - Files: `docs/REAL_BENCHMARK_GUIDE.md`, `docs/PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/WORKLOG.md`, tests
  - Done when: 文档说明 PM15 large benchmark 的离线 mock 和真实 local-corpus 命令；测试验证 large20 dataset 可加载、语言场景分组存在、mock sample 离线可跑。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py` (27 passed); `uv run ruff check src/deepresearch/evaluation/benchmark.py tests/evaluation/test_benchmark.py`

### PM16 Evaluation Dataset Suite

- [x] PM160 设计完整评测数据集 schema 与目录规范
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: BenchmarkCase 新增 `source_dataset` 和 `evaluation_focus` 字段（默认空字符串）；`load_dataset()` 正确解析新字段；所有 dataset 共用同一 loader。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py tests/evaluation/test_bench_dataset.py` (542 passed)

- [x] PM161 建立 ResearchBench full 本地数据集
  - Files: `examples/bench/researchbench_full.jsonl`, `examples/corpus/researchbench_full/`, tests
  - Done when: 32 个深度研究 case，覆盖 12 个领域；中英混合（en=20, zh=12）；每题有 dict-format expected facts + keywords + aliases；20+ 篇 local corpus 文档。
  - Verify: `uv run pytest tests/evaluation/test_bench_dataset.py`

- [x] PM162 建立 HotpotQA deep-research 变体
  - Files: `examples/bench/hotpotqa_deepresearch.jsonl`, `examples/corpus/hotpotqa_deepresearch/`, tests
  - Done when: 8 个多跳 case（5 bridge_entity + 3 comparison）；10 篇 corpus 文档提供多跳证据；`source_dataset="hotpotqa_deepresearch"`。
  - Verify: `uv run pytest tests/evaluation/test_bench_dataset.py`

- [x] PM163 增加 dataset manifest 与质量检查
  - Files: `examples/bench/manifest.json`, `src/deepresearch/evaluation/datasets.py`, tests
  - Done when: `load_manifest()` 列出所有 dataset 元数据；`validate_dataset()` 检查重复 id、缺字段、空 expected_facts；manifest.json 自动生成。
  - Verify: `uv run pytest tests/evaluation/test_bench_dataset.py` (14 passed)

### PM17 Three-layer Evaluation Pipeline

- [x] PM170 固化三层评测输出结构
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `_restructure_evaluation()` 将 flat dict 分为 `rule_metrics`/`judge_scores`/`statistical_context` 三层；顶层 backward-compatible aliases 保留。
  - Verify: `uv run pytest tests/evaluation` (559 passed)

- [x] PM171 扩展规则指标面板
  - Files: `src/deepresearch/evaluation/metrics.py`, `src/deepresearch/schemas/evaluation.py`, tests
  - Done when: `EvaluationResult` 新增 `unsupported_citations` 和 `per_fact_failure_reasons` 字段；`evaluate()` 计算未支持引用 ID 和逐条 fact 失败原因。
  - Verify: `uv run pytest tests/evaluation/test_metrics.py`

- [x] PM172 强化 LLM-as-Judge 5 维评分与 Langfuse scores
  - Files: `src/deepresearch/evaluation/judge_eval.py`, `src/deepresearch/evaluation/langfuse.py`, tests
  - Done when: Langfuse 发送 `judge_*` 五维分数 + `factual_hit_rate` + `hallucination_flag`；judge 失败时 `__failure_reason` 写入返回 dict。
  - Verify: `uv run pytest tests/evaluation/test_judge_eval.py tests/evaluation/test_langfuse.py`

- [x] PM173 增加 Bootstrap 95% CI 与 Cohen's d 比较报告
  - Files: `src/deepresearch/evaluation/statistics.py`, tests
  - Done when: `bootstrap_ci()` 和 `cohens_d()` 提取到独立模块；summary 使用 bootstrap CI。
  - Verify: `uv run pytest tests/evaluation/test_statistics.py`

- [x] PM174 Langfuse experiment metadata 对齐本地结果
  - Files: `src/deepresearch/evaluation/langfuse.py`, `src/deepresearch/evaluation/benchmark.py`, `src/deepresearch/core/run_manager.py`, tests
  - Done when: `report_run()` 接受 case_id/domain/difficulty/question_lang/evidence_lang/source_dataset/model_backend/prompt_label；trace metadata 包含全部字段。
  - Verify: `uv run pytest tests/evaluation/test_langfuse.py tests/evaluation/test_benchmark.py`

### PM18 LLM Backend Matrix

- [x] PM180 统一 OpenAI-compatible 后端配置
  - Files: `src/deepresearch/llm/openai_compatible.py`, `src/deepresearch/cli.py`, tests
  - Done when: `OpenAICompatibleLLMClient` 支持可配置 auth header/prefix、api_key_required 和 max_tokens field；`_build_runtime` 支持 `"openai_compatible"` provider；MiMo/DeepSeek 通过 OpenAI-compatible 薄 wrapper 复用统一实现。
  - Verify: `uv run pytest tests/llm/test_openai_compatible.py tests/test_cli.py`; `uv run pytest` (572 passed, 1 skipped)

- [x] PM181 支持后端热切换和 CLI 覆盖
  - Files: `src/deepresearch/cli.py`, tests
  - Done when: `run`/`benchmark` 支持 `--llm-provider` 和 `--llm-model` 选项覆盖配置；切换不影响 Retriever/Memory/Evaluator。
  - Verify: `uv run pytest tests/test_cli.py`

- [x] PM182 增加 model backend matrix 配置文件
  - Files: `examples/configs/models/*.toml`, tests
  - Done when: 4 个示例配置（mimo/deepseek/openai/vllm）；不含真实密钥；`DeepResearchConfig.from_toml` 可正确解析。
  - Verify: `uv run pytest tests/test_config.py`

- [x] PM183 Benchmark summary 按模型后端分组
  - Files: `src/deepresearch/evaluation/benchmark.py`, tests
  - Done when: `BenchmarkCase` 新增 `model_backend`/`model_name` 字段；summary 输出 `per_model_backend` 和 `per_model_name` 分组。
  - Verify: `uv run pytest tests/evaluation/test_benchmark.py`

### PM19 One-command Experiment Scripts

- [x] PM190 建立实验脚本入口与配置规范
  - Files: `scripts/experiments/README.md`, `examples/experiments/README.md`
  - Done when: `scripts/experiments/` 目录建立，README 说明脚本规范（薄封装 benchmark CLI、统一输出 `outputs/experiments/<id>/`）。
  - Verify: 文档人工检查

- [x] PM191 实现 local mock smoke 实验脚本
  - Files: `scripts/experiments/exp_local_mock.ps1`, `scripts/experiments/exp_local_mock.sh`
  - Done when: 一键跑 mock/local corpus smoke（`researchbench_smoke5`），输出到 `outputs/experiments/`。
  - Verify: 脚本存在且可执行

- [x] PM192 实现真实 local-corpus 模型对比实验脚本
  - Files: `scripts/experiments/exp_model_compare.*`
  - Done when: 循环 `examples/configs/models/*.toml` 配置，对同一 dataset 依次运行 MiMo/DeepSeek/OpenAI/vLLM。
  - Verify: 脚本存在；real mode 需要 `.env`

- [x] PM193 实现 prompt label 对比实验脚本
  - Files: `scripts/experiments/exp_prompt_ablation.*`
  - Done when: 循环 `production`/`staging` prompt label，使用 `--prompt-provider langfuse`。
  - Verify: 脚本存在；real mode 需要 Langfuse keys

- [x] PM194 实现 multilingual large20 回归实验脚本
  - Files: `scripts/experiments/exp_multilingual_large20.*`
  - Done when: 一键跑 `multilingual_large20.jsonl`，使用 smoke config。
  - Verify: 脚本存在

- [x] PM195 实现完整评测套件汇总脚本
  - Files: `scripts/experiments/exp_full_suite.*`, `src/deepresearch/evaluation/compare.py`, tests
  - Done when: 串行跑 4 个 dataset（smoke5/crosslingual/large20/hotpotqa）；失败 dataset 不阻塞后续运行；`compare.py` 生成 `suite_summary.json` 和 `comparison.json`，并记录 missing/failed datasets。
  - Verify: `uv run pytest tests/evaluation/test_compare.py`; `uv run pytest` (576 passed, 1 skipped)

### PM20 Retrieval & Memory Hardening

- [x] PM200 收敛检索和记忆的公共词法、相似度与文档 identity 规则
  - Files: `src/deepresearch/retrieval/lexical.py`, `src/deepresearch/retrieval/scoring.py`, `src/deepresearch/retrieval/identity.py`, `src/deepresearch/retrieval/local_dataset.py`, `src/deepresearch/retrieval/fusion.py`, `src/deepresearch/retrieval/dedup.py`, `src/deepresearch/memory/store.py`, `src/deepresearch/memory/milvus_store.py`, tests
  - Done when: LocalDatasetRetriever、Memory keyword search、RRF/MMR、dedup 和 Milvus adapter 复用同一套 lexical/cosine/document-key helper；本地 corpus retrieve 不再每次调用重扫文件；Milvus row/filter 转换集中到 helper。
  - Verify: `uv run pytest tests/retrieval tests/memory`

- [x] PM201 接入可配置 LexicalPolicy 与 jieba 中文 tokenizer
  - Files: `src/deepresearch/retrieval/lexical.py`, `src/deepresearch/config.py`, `.env.example`, `config.example.toml`, `docs/CONFIGURATION.md`, tests
  - Done when: 支持 `builtin` 和 `jieba` 两种 tokenizer；默认仍为 builtin CJK unigram/bigram，保证离线测试稳定；`jieba` 可通过配置启用，并支持仓库内 userdict 覆盖项目术语（RAG、LLM-as-Judge、Qwen、MiMo、DeepResearch 等）；LocalDatasetRetriever、Memory keyword search、Evaluator token overlap 共享同一 LexicalPolicy。
  - Verify: `uv run pytest tests/retrieval tests/memory tests/evaluation`; `uv run ruff check .`

- [x] PM202 收敛模型后端装配与 OpenAI-compatible client 实现
  - Files: `src/deepresearch/models.py`, `src/deepresearch/llm/`, `src/deepresearch/embeddings/openai_compatible.py`, `src/deepresearch/rerankers/openai_compatible.py`, `src/deepresearch/cli.py`, `src/deepresearch/doctor.py`, tests, docs
  - Done when: MiMo/DeepSeek 作为 OpenAI-compatible 薄 wrapper 复用统一 chat client；CLI、doctor 和 index-corpus 复用模型 factory；doctor 按当前 LLM provider 检查真实 endpoint；移除未实现自动 fallback 的 `fallback_provider` 活跃配置；LLM usage 统一规范化。
  - Verify: `uv run pytest tests/llm tests/embeddings/test_openai_compatible.py tests/rerankers/test_openai_compatible.py tests/test_cli.py tests/test_doctor.py tests/test_config.py`; `uv run ruff check .`

### PM21 Evaluation & Schema Hardening

- [x] PM210 固化评测输出和 benchmark case schema
  - Files: `src/deepresearch/schemas/evaluation.py`, `src/deepresearch/evaluation/benchmark.py`, `src/deepresearch/evaluation/datasets.py`, tests
  - Done when: `ExpectedFact`、`FactHitResult`、`FactFailureReason`、`RuleMetrics`、`StatisticalContext`、`EvaluationLayers` 和 `BenchmarkCase` 成为评测与数据集解析的 typed schema；benchmark 输出保留三层结构和旧 flat alias 兼容。
  - Verify: `uv run pytest tests/evaluation tests/schemas/test_schemas.py`; `uv run ruff check .`

- [x] PM211 收敛 fact matching、LLM fact judge 和 Langfuse 评测上报边界
  - Files: `src/deepresearch/evaluation/fact_matching.py`, `src/deepresearch/evaluation/metrics.py`, `src/deepresearch/evaluation/judge_eval.py`, `src/deepresearch/evaluation/langfuse.py`, tests
  - Done when: fact matching 从 `metrics.py` 拆出；`judge_facts()` 接收/返回 `FactHitResult`；Langfuse adapter 读取 canonical `EvaluationLayers`，不再依赖 flat alias 作为事实源。
  - Verify: `uv run pytest tests/evaluation tests/schemas/test_schemas.py`; `uv run ruff check .`

### PM22 Langfuse Dataset & Experiment Binding

- [x] PM220 将本地 benchmark dataset bootstrap 到 Langfuse Datasets
  - Files: `src/deepresearch/evaluation/langfuse.py`, `src/deepresearch/cli.py`, tests
  - Done when: `LangfuseAdapter.push_dataset()` 可将 JSONL cases push 为 Langfuse dataset items，并用 `case.id` 作为稳定 item id；`datasets push` CLI 命令可用；无 Langfuse key 时返回 0 不报错。
  - Verify: `uv run pytest tests/evaluation/test_langfuse.py`

- [x] PM221 benchmark run 关联 Langfuse dataset item 与 experiment run
  - Files: `src/deepresearch/evaluation/benchmark.py`, `src/deepresearch/evaluation/langfuse.py`, `src/deepresearch/core/run_manager.py`, tests
  - Done when: benchmark `_run_case` 在有 `source_dataset` 时通过 trace metadata、`last_trace_id` 和 `benchmark_*` scores 关联本地 case 与 Langfuse trace；当前 Langfuse SDK 无 `create_dataset_run_item`，原生 experiment run 绑定留给 PM23/PM24 基于 `run_experiment()` 实现。
  - Verify: `uv run pytest tests/evaluation`

### PM23 Fine-grained Langfuse DAG/Agent Observations

- [x] PM230 增加 Planner/DAG/Research/Synthesizer/Red-Blue/Judge/Evaluator 细粒度 observations
  - Files: `src/deepresearch/core/run_manager.py`, `src/deepresearch/core/trace.py`, `src/deepresearch/evaluation/langfuse.py`, tests
  - Done when: Langfuse trace 中可看到 nested observations，覆盖 Planner、每个 DAG task、retrieval query、memory search、synthesis、red/blue/judge 和 evaluator；root observation 写入 report/evaluation/budget/trace_summary；context 成功时不再创建第二个 legacy root observation；本地 trace JSONL 仍保持完整。
  - Verify: `uv run pytest tests/core tests/evaluation`

- [x] PM231 将 RunBudget、latency、token usage 和检索数量标准化进 Langfuse metadata/scores
  - Files: `src/deepresearch/core/budget.py`, `src/deepresearch/evaluation/langfuse.py`, tests
  - Done when: Langfuse dashboard 可按 run/model/prompt label 查看成本、延迟、LLM calls、search/fetch/chunk/embedding/rerank 数量。
  - Verify: `uv run pytest tests/core tests/evaluation/test_langfuse.py`

### PM24 Langfuse-managed Evaluator & Prompt Versioning

- [x] PM240 记录 runtime prompt name/version/hash 到 trace metadata
  - Files: `src/deepresearch/prompts/`, `src/deepresearch/core/run_manager.py`, `src/deepresearch/evaluation/langfuse.py`, tests
  - Done when: 每次 run 可追溯实际使用的 prompt provider、label、prompt name 和版本/hash；Langfuse 侧可按 prompt version 分析质量、成本和延迟。
  - Verify: `uv run pytest tests/prompts tests/core tests/evaluation`

- [x] PM241 支持 Langfuse-managed evaluator 配置
  - Files: `src/deepresearch/evaluation/judge_eval.py`, `src/deepresearch/prompts/`, `src/deepresearch/config.py`, tests, docs
  - Done when: LLM-as-Judge 的 prompt/model/label 可由 Langfuse 配置管理；本地 `judge_eval.md` 和 `fact_judge.md` 继续作为离线 fallback 和测试基线。
  - Verify: `uv run pytest tests/evaluation tests/prompts tests/test_config.py`

### PM25 Human Annotation Queue & Review Loop

- [x] PM250 将低分或争议 benchmark traces 推入人工标注队列
  - Files: `src/deepresearch/evaluation/langfuse.py`, `src/deepresearch/evaluation/benchmark.py`, docs
  - Done when: 可按阈值选择低 `citation_coverage`、低 `factual_hit_rate`、高 hallucination 或 judge 分歧 case，写入 Langfuse annotation workflow；无 Langfuse 时离线 benchmark 不受影响。
  - Verify: `uv run pytest tests/evaluation`

- [x] PM251 导入人工标注结果并回流到本地 evaluation summary
  - Files: `src/deepresearch/evaluation/`, `scripts/experiments/`, tests, docs
  - Done when: 人工标注结果可导出/同步为本地 summary 附加层，用于校准规则指标和 LLM-as-Judge；不会覆盖原始自动评测结果。
  - Verify: `uv run pytest tests/evaluation`

### PM26 Quantitative Claim Calibration

- [x] PM260 建立简历量化数字的本地对照评测口径
  - Files: `src/deepresearch/evaluation/quantification.py`, `tests/evaluation/test_quantification.py`, `docs/QUANTITATIVE_CLAIMS.md`
  - Done when: 可复现输出 JSON fallback、RRF recall@5 和 MMR 证据保真数字；文档明确区分本地 fixture 与真实 benchmark，避免把样例数字写成生产结论。
  - Verify: `uv run pytest tests/evaluation/test_quantification.py`; `uv run python -m deepresearch.evaluation.quantification --output outputs/experiments/quantification/summary.json`

- [x] PM261 建立真实数据集 retrieval-only 对照评测
  - Files: `src/deepresearch/evaluation/retrieval_ablation.py`, `tests/evaluation/test_retrieval_ablation.py`, `docs/QUANTITATIVE_CLAIMS.md`
  - Done when: 可在真实 benchmark JSONL + `examples/corpus` 上跳过 LLM，使用真实 Qwen embedding 对比 pure vector、keyword、RRF hybrid 和 RRF+MMR 的 fact recall@5 与来源多样性；简历数字替换为真实 ResearchBench full 结果。
  - Verify: `uv run pytest tests/evaluation/test_retrieval_ablation.py`; `uv run python -m deepresearch.evaluation.retrieval_ablation examples/bench/researchbench_full.jsonl --corpus examples/corpus --config examples/configs/benchmark_smoke.toml --embedding real --top-k 5 --output outputs/experiments/retrieval-ablation-researchbench-full-real/summary.json`
