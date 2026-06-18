# 检索与资料获取设计

## 1. 设计目标

Research Agent 需要根据子任务目标获取可靠资料，但不应该直接绑定搜索 API、MCP 工具或某个模型厂商的原生搜索能力。项目采用统一 `Retriever` 抽象，让资料来源可替换、可测试、可追踪。

核心目标：

- 可复现：MVP 能用本地资料集稳定跑通。
- 可扩展：后续可以接搜索 API、浏览器、MCP 和模型原生搜索。
- 可引用：所有返回资料必须保留来源、URL、检索时间和元数据。
- 可评测：每次检索都要记录 query、来源、耗时、返回数量和失败原因。

## 2. 架构

```text
Research Agent
  |
  v
Query Generator
  |
  v
Retriever Interface
  |
  +-- LocalDatasetRetriever
  +-- WebSearchRetriever
  +-- MiMoSearchRetriever
  +-- BrowserRetriever
  +-- MCPRetriever
  +-- ModelNativeSearchRetriever
  |
  v
Document Chunker
  |
  v
Embedding + Milvus
  |
  v
Evidence Extraction
```

## 3. Retriever 接口

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

统一输出：

```python
class RetrievedDocument(BaseModel):
    id: str
    title: str
    url: str | None
    source_type: str
    content: str
    published_at: str | None = None
    retrieved_at: str
    metadata: dict = {}
```

## 4. MVP 实现

### 4.1 LocalDatasetRetriever

用途：

- 离线 demo。
- 单元测试和集成测试。
- smoke demo 样例复现。

输入来源：

- `examples/corpus/*.md`
- `examples/corpus/*.jsonl`

处理流程：

1. 加载本地文档。
2. 根据 query 做关键词或 embedding 召回。
3. 返回 `RetrievedDocument`。
4. 写入 Milvus 供后续证据检索。

### 4.2 WebSearchRetriever

用途：

- 接入 Tavily 真实互联网搜索。
- 获取候选 URL、标题和摘要。

MVP 要支持真实搜索 API，同时必须保留 mock 搜索后端保证测试稳定。

后续可接：

- SerpAPI。
- Bing Search API。
- Brave Search API。

### 4.3 MiMoSearchRetriever

用途：

- 接入 MiMo v2.5 Pro 的原生搜索能力。
- 作为 WebSearchRetriever 的补充资料来源。
- 用于对比普通搜索 API 与模型原生搜索的证据质量。

约束：

- Research Agent 不直接调用 MiMo 搜索。
- MiMo 搜索必须通过 `MiMoSearchRetriever` 输出统一 `RetrievedDocument`。
- MiMo 搜索请求使用 OpenAI-compatible chat completions，并通过 `tools` 字段启用 `web_search`。
- 鉴权 header 使用 `api-key: $MIMO_API_KEY`。
- 默认测试不得依赖 MiMo 真实搜索，必须使用 mock。

MiMo 搜索默认参数：

```json
{
  "type": "web_search",
  "max_keyword": 3,
  "force_search": true,
  "limit": 5
}
```

## 5. 后续扩展

### 5.1 BrowserRetriever

负责：

- 网页正文抓取。
- 正文清洗。
- 缓存。
- 去重。
- 失败重试。

推荐工具：

- Playwright。
- trafilatura。
- readability-lxml。

MVP 不实现完整 BrowserRetriever，但实现轻量正文抓取：

- 使用 `httpx` 抓取静态网页。
- 使用 `trafilatura` 清洗正文。
- 动态网页、登录页和反爬页面失败后记录 trace，不阻塞主流程。

### 5.2 MCPRetriever

MCP 是工具接入协议，适合连接外部知识源和工具，不作为 MVP 检索系统的硬依赖。

适合接入：

- GitHub。
- 文件系统。
- 数据库。
- 论文库。
- Notion/Slack/内部知识库。

### 5.3 ModelNativeSearchRetriever

用于接入模型厂商原生搜索能力。

定位：

- fallback。
- baseline 对比。
- 快速 demo。

限制：

- 可控性较弱。
- 缓存和引用链路不一定稳定。
- 不应作为核心检索能力的唯一来源。

## 6. Research Agent 检索流程

1. 根据子任务目标生成 3-5 个 query。
2. 调用 LocalDatasetRetriever、Tavily WebSearchRetriever、MiMoSearchRetriever 或 mock 搜索后端获取候选文档。
3. 对 WebSearchRetriever 返回的 URL 使用 `httpx + trafilatura` 抓取和清洗正文。
4. 按 1200 chars chunk、200 chars overlap 切片，丢弃小于 300 chars 的碎片。
5. 使用 `source_url + content_hash` 去重。
6. 使用 Qwen3-Embedding-4B 生成 2560 维 embedding。
7. 写入 Milvus，附带 `run_id`、`task_id`、`source_type` 等 scalar fields。
8. 从 Milvus 按向量相似度和标量过滤召回 top 30 证据片段。
9. 使用 bge-reranker-v2-m3 rerank 到 top 8。
10. MiMo v2.5 Pro 从证据片段中抽取 claim、quote、citation 和 confidence。
11. 将结构化证据交给 Synthesizer 和 Memory。

默认成本控制：

- `max_queries_per_task = 5`
- `max_docs_per_task = 20`
- `max_chunks_per_task = 80`
- `max_llm_calls_per_run = 80`

## 6.1 Post-MVP：RRF 融合

Post-MVP 第一项检索质量增强是 RRF（Reciprocal Rank Fusion）。RRF 适合本项目，因为 Tavily、MiMo Search、LocalDataset、Milvus recall 的分数尺度不同，直接比较 raw score 不可靠。RRF 只依赖 rank，工程上更稳。

标准公式：

```text
score(d) = sum(1 / (rrf_k + rank_i(d)))
```

默认参数：

- `rrf_k = 60`
- `max_fused_results = 20`

第一版做 document-level RRF：

```text
multi-query search results -> RRF -> fetch top docs -> chunk
```

输入：

- Tavily 每个 query 的搜索结果。
- MiMoSearch 每个 query 的搜索结果。
- LocalDatasetRetriever 的 ranked results。

输出：

- 去重后的 `RetrievedDocument` 列表。

去重 key：

- `canonical_url` 优先。
- 无 URL 时使用 `title + content_hash`。

第二版做 chunk-level RRF：

```text
Milvus multi-query vector recall + independent keyword recall -> RRF -> reranker
```

chunk 去重 key：

- `source_url + content_hash`

暂不做动态权重。需要对比实验时再扩展 weighted RRF：

```text
weighted_score(d) = sum(weight_i / (rrf_k + rank_i(d)))
```

## 6.2 Post-MVP：MMR 去冗余与覆盖面控制

MMR（Maximal Marginal Relevance）不是 RRF 的替代，而是 RRF 后面的 context selection 策略。

- RRF 负责把多 query、多 retriever、多 recall source 的候选结果融合成统一 ranked list。
- MMR 负责从候选 chunks 中选择既相关又不重复的一组上下文，避免多个 chunk 都在讲同一个事实。

第一版只在 chunk 级别做 MMR：

```text
document-level RRF -> fetch -> chunk -> chunk-level RRF/rerank -> MMR -> context pack
```

默认参数：

- `mmr_lambda = 0.7`
- `max_context_chunks = 12`
- chunk 相似度使用 embedding cosine similarity

MMR scoring：

```text
score(candidate) =
  mmr_lambda * relevance(candidate)
  - (1 - mmr_lambda) * max_similarity(candidate, selected_chunks)
```

`relevance(candidate)` 第一版优先使用 reranker score；没有 reranker score 时使用 query/chunk embedding cosine similarity，最后回退到 RRF score。

关键词 recall 第一版不依赖 vector recall 候选集：MemoryStore 按 run/task/source_type 独立读取候选，使用英文/数字词项和中文单字、双字 token 做词法覆盖率排序。后续可替换为 Milvus BM25/full-text search adapter。

MMR 的目标指标：

- 降低最终 context 中的重复 chunk 比例。
- 提升不同 source 覆盖率。
- 提升 synthesis 可用 evidence 数量。
- 不显著降低最终答案事实准确率。

## 7. Trace 记录

每次检索记录：

- `run_id`
- `task_id`
- `retriever`
- `query`
- `started_at`
- `finished_at`
- `duration_ms`
- `result_count`
- `error`
- `source_urls`

这样可以在失败分析和评测中区分是检索失败、证据不足，还是报告合成问题。
