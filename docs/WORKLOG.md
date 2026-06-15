# Worklog

只记录最近关键工作记录、验证结果和阻塞点，插到最后。不要记录模型临时思考过程。

## Recent

- 2026-06-15: 建立项目规划文档，明确 PRD、MVP、实现规划、技术栈和 Retriever 设计。
- 2026-06-15: 确认 AGENTS.md 规则：AI 优先、中文为主、使用 uv、禁止 Agent 框架作为核心编排层、默认测试离线可跑、维护 TASKS/WORKLOG。
- 2026-06-15: 固化模型与检索策略：MiMo v2.5 Pro 作为默认模型，DeepSeek fallback，Qwen3-Embedding-4B 1024 维，bge-reranker-v2-m32 reranker，支持真实 Web 搜索与 MiMo 原生搜索。
- 2026-06-15: 固化剩余实现细节：MiMo 使用 OpenAI-compatible chat completions 且 header 为 `api-key`，真实搜索使用 Tavily，MVP 使用 `httpx + trafilatura` 抓取正文，chunk 为 1200/200，去重为 `source_url + content_hash`。
- 2026-06-15: 重写 `docs/TASKS.md` 为可执行 MVP backlog，按 M0-M9 里程碑拆分任务，每个任务包含文件范围、完成标准和验证命令。
- 2026-06-15: 将 unborn 分支从 `master` 重命名为 `main`，并确定第一次 commit 后创建 `develop` 作为日常开发分支。
- 2026-06-15: 准备首次提交：补充 `.gitignore` 本地配置与运行产物规则，切换到 `develop` 作为日常开发分支。
- 2026-06-15: Claude 完成 M1 项目骨架与工具链；复核通过 `uv run deepresearch --help`、`uv run deepresearch run --help`、`uv run deepresearch index-corpus --help`、`uv run pytest`、`uv run ruff check .`。
- 2026-06-15: Review 并修复 M2：配置层不再把真实 API key 覆盖到 `api_key_env` 字段，TraceEventType 对齐文档中的细粒度结构化事件。
- 2026-06-15: Review 并修复 M3：MiMo `thinking` 使用对象格式，LLM 参数保留显式 0 值，embedding normalize 配置实际生效。
- 2026-06-15: 完成 M1 项目骨架与工具链（T009-T013）：src layout 10 个子包、pyproject.toml 依赖 + CLI entry、Ruff + pytest markers、`.env.example` + `config.example.toml`。验证：`uv run deepresearch --help`、`uv run pytest`、`uv run ruff check .`。
- 2026-06-15: 完成 M2 配置、Schema 与 Trace（T020-T024）：DeepResearchConfig 12 section + 优先级链、6 核心 Pydantic schema、9 状态状态机 + 合法流转表、JSON fallback 6 层策略、TraceLogger JSONL 9 种事件类型。共 80 个测试通过。
- 2026-06-15: 完成 M3 模型抽象（T030-T036）：LLMClient + MockLLM + MiMo/DeepSeek client、EmbeddingClient + mock + OpenAI-compatible Qwen、RerankerClient + mock + OpenAI-compatible bge。MiMo 使用 `api-key` header，DeepSeek 使用 Bearer auth。共 123 个测试通过。
- 2026-06-15: 完成 M4 Retriever、正文抓取与切片（T040-T046）：Retriever 抽象 + MockRetriever、LocalDatasetRetriever 关键词召回、Tavily WebSearchRetriever、MiMoSearchRetriever（tools.web_search）、WebFetcher（httpx+trafilatura）、chunking（1200/200/300）、dedup（source_url+content_hash）。共 166 个测试通过。
- 2026-06-15: 完成 M5 Milvus MemoryStore（T050-T053）：MemoryStore 抽象 + MockMemoryStore（cosine similarity + 标量过滤）、MilvusStore（两个 collection、FloatVector 1024、COSINE+HNSW、upsert/search/delete/query）、export_snapshot JSONL 导出。共 189 个测试通过。
- 2026-06-15: 完成 M6 DAG 与执行器（T060-T063）：DAG 数据结构（依赖解析、ready task、cycle detection、topological sort）、异步 DAGExecutor（Semaphore 并发控制、PENDING→READY→RUNNING 状态链、blocked task 传播跳过）、task timeout + retry + global timeout + cancellation。replan 支持连续失败、同层失败率 >= 40%、零 evidence 和 information_insufficient 四类触发，并输出任务级/层级动作与 Limitations；全局超时携带 partial result 供强制合成。修复混合依赖状态导致下游任务等待至全局超时的问题。共 233 个测试通过。
- 2026-06-15: 完成 M7 Agents 与报告生成（T070-T072）：PlannerAgent 对空计划、重复 ID、未知依赖和循环依赖执行 DAG 校验与 fallback；ResearchAgent 完成 3-5 query→retrieve→正文 fetch→chunk/dedup→embedding→Milvus 写入/召回→rerank top 8→evidence 抽取全链路，使用 source_id 和原文 quote 校验保证证据可追溯，并输出 evidence_count/information_insufficient 对接 replan；Synthesizer 校验完整 E-id、拒绝未知引用并将无证据 claim 移入 Limitations。MockLLM 改为语义路由并保留自定义响应队列，消除 Agent 调用顺序耦合。共 247 个测试通过。
- 2026-06-15: 完成 M8 Red-Blue 与 Evaluator（T080-T083）：RedAgent 使用强类型 issue 和 0-1 score 校验；BlueAgent 将 ADD/DELETE/MODIFY/VERIFY 安全应用到报告副本，ADD/MODIFY 强制绑定现有 evidence，DELETE 要求精确文本，VERIFY 写入 Limitations；Judge 驱动 Red→Blue→Red 闭环，以复审 Red score 判断 target/max rounds/连续低增益/重复 issue 震荡；Evaluator 仅使用正文计算 citation coverage，References 不再污染指标，并适配独立 summary/limitations/references 字段计算完整度。共 269 个测试通过。
- 2026-06-15: 完成 M9 CLI、RunManager 与 Smoke Demo（T090-T093）：RunManager 贯通 run_id、Researcher、Memory、Synthesizer、Red-Blue-Judge 和 Evaluator，支持全局超时后 partial synthesis，并输出 report.md、trace.jsonl、memory_snapshot.jsonl、evaluation.json；CLI 提供显式 mock/real 装配，真实模式按配置初始化 MiMo/DeepSeek、Tavily/MiMo/local retriever、OpenAI-compatible embedding/reranker 和 Milvus，缺少凭据时快速失败；init 创建 TOML，index-corpus 实际执行 chunk、embedding 和 Milvus 写入；mock smoke 验证报告引用、指标、memory 和全链路 trace。MVP 全部里程碑完成。共 285 个测试通过。
- 2026-06-15: 首次真实 Tavily 端到端验收暴露两个问题：Research task 因串行检索/抓取连续触发 180 秒超时，Windows 环境不适合本地文件型 Milvus；决定 MVP 直接使用 Docker Milvus Standalone，并开始修复并发边界、配置限额和阶段 trace。
- 2026-06-15: 完成真实 Tavily + Milvus Standalone 验收：endpoint 实际返回 `Qwen3-Embedding-4B` 2560 维，可用 reranker 为 `bge-reranker-v2-m3`；使用 2560 维 collection 后 run `369ea50b8852` 任务成功率 1.0、引用覆盖率 0.8571、报告完整度 1.0。
- 2026-06-15: 修复真实报告 References 只输出来源标题、不输出 URL 的问题；Synthesizer evidence context 和最终 References 现在都会保留 `source_url`。
- 2026-06-15: 清理 Milvus Lite / 本地 `.db` 测试残留，MilvusStore 默认只按 Docker Milvus Standalone URI 连接。
- 2026-06-15: 补充 Post-MVP Roadmap 和任务 backlog：优先 `doctor`，随后做 RRF、引用质量、真实 replan、trace inspect、Memory schema version 和小型 benchmark。
- 2026-06-15: 完成 PM0 真实环境自检与工程可靠性（PM001-PM003）：`deepresearch doctor --real` 可检查 MiMo、Tavily、embedding、reranker 和 Milvus Standalone schema；新增 `httpx[socks]` 支持 SOCKS 代理；integration smoke 需显式 `DEEPRESEARCH_RUN_REAL_INTEGRATION=1`；MilvusStore 迁移到 MilvusClient 并在 connect 阶段校验 embedding 维度。共 308 个测试通过、1 个真实集成测试默认跳过。
