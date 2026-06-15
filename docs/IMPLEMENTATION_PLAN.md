# 项目实现规划

## 1. 总体架构

```text
CLI/API
  |
  v
Run Manager
  |
  v
Planner -> Task DAG
  |
  v
DAG Executor -----> Trace Logger
  |
  +--> Research Agent
  +--> Memory Store
  |
  v
Synthesizer
  |
  v
Red Agent -> Blue Agent -> Judge
  |
  v
Evaluator
  |
  v
Report + Trace + Metrics
```

## 2. 推荐目录结构

```text
deepresearch/
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
  cli.py
tests/
docs/
examples/
outputs/
```

## 3. 核心模块设计

### 3.1 Run Manager

职责：

- 创建 run_id。
- 加载配置。
- 初始化 LLM、Memory、Executor、Trace Logger。
- 管理一次研究任务的生命周期。
- 将最终产物写入 `outputs/<run_id>/`。

### 3.2 Planner

输入：

- 用户研究问题。
- 报告深度。
- 最大子任务数。
- 可用工具列表。

输出：

- `ResearchPlan`
- `TaskNode[]`
- 任务依赖边。

实现要点：

- 先要求 LLM 输出严格 JSON。
- 用 Pydantic 校验。
- 校验失败时触发 JSON fallback。
- DAG 必须检查无环。

### 3.3 DAG Executor

职责：

- 找出所有依赖已完成的 `READY` 任务。
- 使用 `asyncio.Semaphore` 控制并发。
- 处理任务超时、失败、重试和跳过。
- 在全局超时时触发强制合成。

建议状态流转：

```text
PENDING -> READY -> RUNNING -> SUCCEEDED
                         |-> FAILED -> RETRYING -> RUNNING
                         |-> FAILED -> REPLANNING
                         |-> FAILED -> SKIPPED
RUNNING -> CANCELLED
```

默认参数：

```toml
max_task_retries = 2
task_timeout_seconds = 180
global_timeout_seconds = 1800
max_concurrency = 4
```

replan 触发条件：

- 单任务连续失败 2 次。
- 某个任务提取到的 evidence 数量为 0。
- 同一层 DAG 中失败任务比例 >= 40%。
- Research Agent 返回 `information_insufficient`。

replan 行为优先级：

1. 新增替代任务。
2. 修改检索 query。
3. 跳过失败任务，并在最终报告 `Limitations` 中记录。

三级降级：

1. 单任务失败：retry + alternate queries。
2. 批量失败：replan 当前 DAG 层。
3. 全局超时：强制合成 partial report，并明确列出失败任务和证据不足结论。

成本控制默认值：

```toml
max_queries_per_task = 5
max_docs_per_task = 20
max_chunks_per_task = 80
max_llm_calls_per_run = 80
```

### 3.4 Research Agent

职责：

- 根据任务目标生成多个检索 query。
- 通过 Retriever 接口获取候选资料。
- 提取证据。
- 生成子任务结论。
- 将证据写入 Memory。

输出格式：

```json
{
  "task_id": "task_001",
  "summary": "...",
  "claims": [
    {
      "claim": "...",
      "evidence_ids": ["ev_001"],
      "confidence": 0.82
    }
  ],
  "evidence": [
    {
      "id": "ev_001",
      "source": "...",
      "quote": "...",
      "retrieved_at": "2026-06-15"
    }
  ]
}
```

### 3.5 Retriever

Retriever 是资料获取层，负责把子任务目标转成可引用的候选文档。Research Agent 不直接调用搜索 API、MCP 或模型原生搜索。

接口形态：

```python
class Retriever:
    async def retrieve(
        self,
        queries: list[str],
        *,
        run_id: str,
        task_id: str,
        top_k: int,
    ) -> list[RetrievedDocument]:
        ...
```

核心输出：

```json
{
  "id": "doc_001",
  "title": "...",
  "url": "https://example.com/article",
  "source_type": "web",
  "content": "...",
  "published_at": "2026-04-01",
  "retrieved_at": "2026-06-15",
  "metadata": {
    "query": "...",
    "retriever": "web_search"
  }
}
```

MVP 实现：

- `LocalDatasetRetriever`：读取 `examples/corpus/*.md` 或 `.jsonl`，用于可复现测试。
- `WebSearchRetriever`：通过通用接口调用搜索 provider。
- `TavilySearchProvider`：MVP 默认真实搜索 provider。
- `MiMoSearchRetriever`：调用 MiMo v2.5 Pro 原生搜索，输出统一 `RetrievedDocument`。
- `MockSearchProvider`：用于离线测试。

MiMo 调用约定：

- URL: `https://api.xiaomimimo.com/v1/chat/completions`
- Header: `api-key: $MIMO_API_KEY`
- Search tool: `{"type": "web_search", "max_keyword": 3, "force_search": true, "limit": 5}`

后续实现：

- `BrowserRetriever`：抓取网页正文、清洗正文、缓存、去重。
- `MCPRetriever`：通过 MCP 接入外部工具和知识源。
- `ModelNativeSearchRetriever`：接入模型厂商原生搜索能力，作为 fallback 或对比实验。

检索流程：

1. Research Agent 根据子任务目标生成 3-5 个 query。
2. Retriever 返回候选文档。
3. 对 URL 使用 `httpx + trafilatura` 做轻量正文抓取和清洗。
4. 按 1200 chars chunk、200 chars overlap 切片，丢弃小于 300 chars 的碎片。
5. 使用 `source_url + content_hash` 去重。
6. 使用 Qwen3-Embedding-4B 生成 1024 维 embedding。
7. chunk、embedding 和元数据写入 Milvus。
8. Research Agent 从 Milvus 召回 top 30 证据片段。
9. 使用 bge-reranker-v2-m32 rerank 到 top 8。
10. MiMo v2.5 Pro 从证据片段中抽取 claim、quote 和 citation。

正文抓取约束：

- MVP 使用 `httpx + trafilatura`。
- Playwright 放到后续 `BrowserRetriever`。
- 抓取失败记录 trace，不阻塞主流程。

### 3.5.1 Embedding 与 Reranker

Embedding 和 reranker 都通过 OpenAI-compatible endpoint 调用，但必须走统一抽象层。

Embedding 默认参数：

- model: `Qwen3-Embedding-4B`
- dim: `1024`
- batch size: `32`
- timeout: `60s`
- max retries: `2`
- normalize: `false`

说明：Qwen3-Embedding-4B 默认会做 L2 归一化，系统层不重复归一化；如果后续接入未归一化模型，再通过配置打开 normalize。

Reranker 默认参数：

- model: `bge-reranker-v2-m32`
- batch size: `16`
- timeout: `60s`
- max retries: `2`

### 3.6 Memory Store

MVP 直接使用 Docker Milvus Standalone 作为语义记忆与证据向量库。Agent 执行 trace、报告产物和评测结果先落盘为 JSON/JSONL；需要关系查询的元数据在 Milvus scalar fields 中冗余保存，后续再按需要引入 PostgreSQL 做结构化分析库。

核心 collection：

- `deepresearch_chunks`：外部资料切片、网页内容、证据候选。
- `deepresearch_memories`：Agent 摘要、claim、结论、冲突记录。

核心字段：

- `id`
- `run_id`
- `task_id`
- `agent_role`
- `source_url`
- `source_type`
- `title`
- `content`
- `summary`
- `claim`
- `confidence`
- `created_at`
- `metadata_json`
- `embedding: FloatVector(1024)`

索引配置：

- metric type: `COSINE`
- index type: `HNSW`

MVP 检索策略：

- Milvus 向量相似度检索。
- 基于 `run_id`、`task_id`、`source_type`、`confidence` 的标量过滤。
- 关键词 fallback 使用本地 JSONL 快照或简单倒排索引。
- 合并去重后返回 top-k。

### 3.7 Synthesizer

职责：

- 从所有任务结果和 Memory 中取证据。
- 生成 Markdown 报告。
- 对关键结论插入引用。
- 输出局限性。

报告结构：

- 标题。
- 摘要。
- 研究问题与方法。
- 分主题分析。
- 关键发现。
- 风险与局限。
- 结论。
- 参考来源。

引用格式：

- 报告使用 Markdown。
- 关键 claim 使用 evidence id 引用，例如 `[E12]`。
- 每个关键 claim 至少绑定 1 个 evidence id。
- 没有证据支撑的判断必须放入“局限性”或“推测”部分，不能写成确定结论。

参考来源格式：

```markdown
## References

[E12] Title - https://example.com
Retrieved at: 2026-06-15
Evidence: quoted snippet...
```

### 3.8 Red-Blue-Judge

Red Agent 输出问题清单：

```json
{
  "issues": [
    {
      "type": "citation_missing",
      "severity": "high",
      "location": "关键发现 2",
      "description": "...",
      "suggested_action": "VERIFY"
    }
  ],
  "score": 0.72
}
```

Blue Agent 根据问题执行修复：

- `ADD`：补充缺失信息。
- `DELETE`：删除无证据支持内容。
- `MODIFY`：改写不准确表述。
- `VERIFY`：补充引用或重新查证。

Judge 判断：

- 修复后分数是否提高。
- 是否出现重复修改。
- 是否达到停止条件。

终止条件：

- 最大轮数为 3。
- Red score >= 0.85。
- 连续两轮分数提升 < 0.03。
- 同类 issue 在同一位置重复出现 2 次，判定震荡并停止。

### 3.9 Evaluator

MVP 指标：

- `task_success_rate`
- `citation_coverage`
- `empty_citation_rate`
- `report_section_completeness`
- `red_issue_count`
- `blue_fix_count`

后续指标：

- LLM-as-Judge 五维评分。
- Bootstrap 95% CI。
- Cohen's d。
- 不同模型、不同策略的对比实验。

### 3.10 JSON fallback

Agent 结构化输出解析使用本地规则修复，不调用 LLM 修 JSON。

顺序：

1. `json.loads` strict 解析。
2. 提取 Markdown ```json code block。
3. 从文本中截取第一个 `{...}` 或 `[...]`。
4. 本地规则修复：去尾逗号、替换中文引号、补缺失字段默认值。
5. Pydantic 校验。

如果仍失败，任务进入 `FAILED`，由状态机处理。

### 3.11 Trace schema

trace 是结构化事件流，不是普通文本日志。每个 run 输出：

```text
outputs/<run_id>/trace.jsonl
```

每行一个 JSON：

```json
{
  "event_id": "evt_001",
  "run_id": "run_001",
  "task_id": "task_003",
  "event_type": "task_state_changed",
  "from_state": "READY",
  "to_state": "RUNNING",
  "timestamp": "2026-06-15T10:00:00Z",
  "metadata": {}
}
```

核心事件类型：

- `planner_created_plan`
- `task_state_changed`
- `retriever_called`
- `milvus_upserted`
- `milvus_searched`
- `llm_called`
- `red_review_created`
- `blue_fix_applied`
- `evaluation_completed`

## 4. 实施顺序

1. 建立数据模型和配置系统。
2. 实现 Mock LLM，保证无需 API 也能跑测试。
3. 实现 Planner 的 JSON 输出和校验。
4. 实现 DAG Executor 与状态机。
5. 实现 LLMClient、EmbeddingClient、RerankerClient 和 mock 后端。
6. 实现 Retriever 接口、LocalDatasetRetriever、Tavily WebSearchRetriever、MiMoSearchRetriever 和 mock 搜索后端。
7. 实现 `httpx + trafilatura` 正文抓取、chunk 和去重。
8. 实现 Milvus MemoryStore，包括 collection 初始化、upsert、search、delete 和快照导出。
9. 实现 Research Agent。
10. 实现 Synthesizer。
11. 实现 Red-Blue 一轮修复。
12. 实现 Evaluator 和输出落盘。
13. 增加真实 LLM 后端。
14. 增加示例任务和测试。

## 5. 测试计划

### 单元测试

- DAG 无环检测。
- 任务依赖解析。
- 状态机合法流转。
- Executor 并发限制。
- 超时和重试。
- JSON fallback。
- Retriever query 生成、去重、失败 fallback。
- chunk、content hash 去重、正文抓取失败 fallback。
- EmbeddingClient 和 RerankerClient mock 测试。
- Memory 去重。
- 指标计算。

### 集成测试

- Mock LLM 端到端运行。
- Milvus collection 初始化、upsert、search。
- 单个任务失败后继续合成。
- Red-Blue 修复后生成新报告。

测试 marker：

- `unit`
- `integration`
- `e2e`
- `slow`
- `network`
- `milvus`
- `llm`

默认 `uv run pytest` 必须在无 API key、无互联网、无 Milvus Standalone 时通过。Tavily 搜索、MiMo 搜索、DeepSeek fallback、embedding/reranker 真实 endpoint、Milvus Standalone 测试必须打 marker。

### 回归测试

- 固定 3 个示例问题。
- 对比每次输出的结构完整度、引用覆盖率和任务成功率。

## 6. 风险与应对

- LLM 输出不稳定：使用 Pydantic schema、JSON fallback 和 mock 测试。
- 检索质量不足：MVP 支持本地资料集，并用 Milvus 标量过滤约束检索范围，避免只依赖全局向量相似度。
- 外部搜索不稳定：Research Agent 依赖 Retriever 接口，MVP 提供 LocalDatasetRetriever 和 mock 搜索后端保证测试可复现。
- Milvus 运维成本偏高：MVP 提供 Docker Compose 启动 Milvus Standalone，并保留 Mock MemoryStore 测试替身。
- 多 Agent 成本高：限制最大任务数、最大轮数和上下文长度。
- Red-Blue 循环震荡：设置最大轮数、分数阈值和重复 issue 检测。
- 评测主观性强：规则指标先落地，LLM-as-Judge 作为补充。
