# 配置设计

## 1. 配置格式

项目使用 TOML 作为配置文件格式。

配置文件路径优先级：

1. `--config` 指定路径。
2. `DEEPRESEARCH_CONFIG_PATH`。
3. `./config.toml`。
4. `~/.config/deepresearch/config.toml`。
5. `/etc/deepresearch/config.toml`。
6. 内置默认值。

配置值优先级：

1. CLI 参数。
2. 配置文件中的显式字段。
3. 环境变量。
4. 内置默认值。

## 2. 默认配置

```toml
[llm]
provider = "mimo"
model = "mimo-v2.5-pro"
base_url = "https://api.xiaomimimo.com/v1"
api_key_env = "MIMO_API_KEY"
api_key_header = "api-key"
fallback_provider = "deepseek"
max_completion_tokens = 1024
temperature = 1.0
top_p = 0.95
thinking = "disabled"

[embedding]
provider = "openai_compatible"
model = "Qwen3-Embedding-4B"
dim = 2560
base_url = ""
api_key_env = "DEEPRESEARCH_EMBEDDING_API_KEY"
batch_size = 32
timeout_seconds = 60
max_retries = 2
normalize = false
request_dimensions = false

[reranker]
provider = "openai_compatible"
model = "bge-reranker-v2-m3"
base_url = ""
api_key_env = "DEEPRESEARCH_RERANKER_API_KEY"
batch_size = 16
timeout_seconds = 60
max_retries = 2

[milvus]
uri = "http://localhost:19530"
chunks_collection = "deepresearch_chunks"
memories_collection = "deepresearch_memories"
metric_type = "COSINE"
index_type = "HNSW"

[retrieval]
providers = ["local_dataset", "web_search", "mimo_search"]
top_k_documents = 20
top_k_vector = 30
top_k_reranked = 8
search_provider = "tavily"
max_queries_per_task = 5
max_docs_per_task = 20
max_chunks_per_task = 80

[web_search]
provider = "tavily"
api_key_env = "TAVILY_API_KEY"
timeout_seconds = 30
max_retries = 2

[mimo_search]
enabled = true
max_keyword = 3
force_search = true
limit = 5

[fetch]
enabled = true
timeout_seconds = 20
max_retries = 2
user_agent = "DeepResearchAgent/0.1"

[chunking]
chunk_size_chars = 1200
chunk_overlap_chars = 200
min_chunk_chars = 300

[dedup]
strategy = "source_url_content_hash"

[executor]
max_concurrency = 4
max_task_retries = 2
task_timeout_seconds = 180
global_timeout_seconds = 1800
max_llm_calls_per_run = 80

[red_blue]
max_rounds = 3
target_score = 0.85
min_score_delta = 0.03
oscillation_window = 2

[synthesizer]
report_profile = "tech_research"

[evidence_quality]
min_confidence = 0.3
min_token_overlap = 0.1

[fusion]
rrf_k = 60
max_fused_docs = 20
max_fused_chunks = 30
mmr_lambda = 0.7
max_mmr_results = 12
```

## 3. 环境变量

```env
DEEPRESEARCH_CONFIG_PATH=
DEEPRESEARCH_LLM_PROVIDER=mimo
DEEPRESEARCH_LLM_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_API_KEY=
DEEPRESEARCH_LLM_MODEL=mimo-v2.5-pro
DEEPRESEARCH_FALLBACK_LLM_PROVIDER=deepseek
DEEPRESEARCH_EMBEDDING_BASE_URL=
DEEPRESEARCH_EMBEDDING_API_KEY=
DEEPRESEARCH_EMBEDDING_MODEL=Qwen3-Embedding-4B
DEEPRESEARCH_EMBEDDING_DIM=2560
DEEPRESEARCH_EMBEDDING_REQUEST_DIMENSIONS=false
DEEPRESEARCH_RERANKER_BASE_URL=
DEEPRESEARCH_RERANKER_API_KEY=
DEEPRESEARCH_RERANKER_MODEL=bge-reranker-v2-m3
DEEPRESEARCH_REPORT_PROFILE=tech_research
DEEPRESEARCH_EVIDENCE_MIN_CONFIDENCE=0.3
DEEPRESEARCH_EVIDENCE_MIN_TOKEN_OVERLAP=0.1
DEEPRESEARCH_RRF_K=60
DEEPRESEARCH_MAX_FUSED_DOCS=20
DEEPRESEARCH_MAX_FUSED_CHUNKS=30
DEEPRESEARCH_MMR_LAMBDA=0.7
DEEPRESEARCH_MAX_MMR_RESULTS=12
DEEPRESEARCH_MILVUS_URI=http://localhost:19530
DEEPRESEARCH_MILVUS_CHUNKS_COLLECTION=deepresearch_chunks
DEEPRESEARCH_MILVUS_MEMORIES_COLLECTION=deepresearch_memories
DEEPRESEARCH_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
```

`.env` 不提交仓库，`.env.example` 可以提交。

注意：不同 OpenAI-compatible endpoint 暴露的模型名和 embedding 维度可能不同。当前真实验收环境的 `/models` 显示 `Qwen3-Embedding-4B` 为 2560 维，可用 reranker 为 `bge-reranker-v2-m3`；这种情况下需要设置 `DEEPRESEARCH_EMBEDDING_DIM=2560` 和 `DEEPRESEARCH_RERANKER_MODEL=bge-reranker-v2-m3`，并使用匹配维度的新 Milvus collection。

## 4. CLI

```bash
uv run deepresearch init
uv run deepresearch run "question"
uv run deepresearch run "question" --config ./config.toml
uv run deepresearch index-corpus
uv run deepresearch eval <run_id>
uv run deepresearch inspect <run_id>
uv run deepresearch config
```

## 5. MiMo 调用约定

MiMo v2.5 Pro 使用 OpenAI-compatible chat completions 路径，但鉴权 header 使用 `api-key`。

```text
POST https://api.xiaomimimo.com/v1/chat/completions
api-key: $MIMO_API_KEY
Content-Type: application/json
```

MiMo 原生搜索通过 chat completion 的 `tools` 字段启用，并封装在 `MiMoSearchRetriever` 中。业务层不得直接拼接 MiMo 搜索请求。
