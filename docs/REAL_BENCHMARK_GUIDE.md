# Real Benchmark Guide

## 完整真实 Benchmark + Langfuse 上报

当前建议优先使用 Local Corpus 路径做真实评测。The primary benchmark path uses a local corpus. Real-time web search (Tavily, MiMo Search) is an optional network enhancement layer, not required for benchmark evaluation. Local corpus benchmark 的目标是验证”给定可控资料后，系统能否稳定抽取证据、生成引用、降低幻觉”，而不是验证搜索 API 的额度和稳定性。

### 1. 环境准备

```bash
# 启动 Milvus
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest

# 配置环境变量（编辑 .env）
cat >> .env << 'EOF'
MIMO_API_KEY=your-mimo-key
TAVILY_API_KEY=your-tavily-key
DEEPRESEARCH_EMBEDDING_BASE_URL=https://your-embedding-endpoint/v1
DEEPRESEARCH_EMBEDDING_API_KEY=your-embedding-key
DEEPRESEARCH_EMBEDDING_DIM=2560
DEEPRESEARCH_RERANKER_BASE_URL=https://your-reranker-endpoint/v1
DEEPRESEARCH_RERANKER_API_KEY=your-reranker-key
DEEPRESEARCH_LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
DEEPRESEARCH_EXPERIMENT_NAME=deepresearch-bench-v1
EOF

# 验证环境
uv run deepresearch doctor --real
```

### 2. 推荐路径：Local Corpus Benchmark

本地资料集放在 `examples/corpus/`。每个 benchmark case 对应 2-4 篇短文档，文档需要覆盖 expected facts 和可引用原文。

目标命令：

```bash
uv run deepresearch benchmark \
  examples/bench/researchbench_smoke5.jsonl \
  --mode real \
  --retriever local \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --output outputs/bench-local \
  --experiment pm8-local-smoke
```

说明：

- `--mode real` 仍使用真实 MiMo chat、embedding、reranker 和 Milvus。
- `--retriever local` 避免消耗 Tavily/MiMo 搜索额度。
- `outputs/bench-local` 不提交，只用于本地复测。

### 3. Optional: Network-Enhanced Retrieval

> **Note:** This path costs real API credits (Tavily, MiMo Search) and produces non-reproducible results. Not recommended for benchmark evaluation.

```bash
uv run deepresearch benchmark \
  examples/bench/researchbench_mini.jsonl \
  --mode real \
  --output outputs/bench-$(date +%Y%m%d)
```

联网 benchmark 仅作为增强验证，不作为默认验收路径。使用前确认 Tavily/MiMo 搜索额度充足。搜索结果受时间、额度和网络波动影响，不适合调优 evidence extraction 和 citation coverage。

### 4. 查看结果

```bash
# 汇总指标
cat outputs/bench-*/summary.json | python -m json.tool

# 单个 case 详情
uv run deepresearch inspect <run-id> --timeline

# Langfuse dashboard
open https://cloud.langfuse.com
```

### 5. 归档报告样例

选择效果好的 run 归档：

```bash
RUN_ID=<best-run-id>

# 脱敏归档（去除 trace 全量和密钥）
cp outputs/$RUN_ID/report.md docs/examples/sample-report.md
cp outputs/$RUN_ID/evaluation.json docs/examples/sample-evaluation.json

# benchmark summary
cp outputs/bench-*/summary.json docs/examples/sample-bench-summary.json
```

### 6. 预期指标

| 指标 | 预期范围 |
|------|----------|
| task_success_rate | 0.8–1.0 |
| citation_coverage | 0.6–0.9 |
| factual_hit_rate | 0.5–0.8 |
| hallucination_flag_count | 0–3 |
| avg_elapsed_seconds | 30–120s |

### 7. 故障排查

```bash
# Milvus 连接失败
docker ps | grep milvus
curl http://localhost:19530/healthz

# LLM API 限流
# 检查 trace.jsonl 中的 error 字段

# Tavily 额度/限流
# trace.jsonl 中出现 HTTP 432 时，切换到 --retriever local 或 MiMo Search；
# benchmark 主路径不要依赖 Tavily 免费额度。
# Tavily adapter 会在 provider 错误后返回空结果，不让单次搜索错误直接打断 DAG。

# Embedding 维度不匹配
uv run deepresearch doctor --real  # 会检查 dim
```

## Quick Start: Local Corpus Smoke Benchmark

The recommended stable benchmark path uses a local corpus instead of real-time web search:

```bash
# Prerequisites: real LLM/embedding/reranker/Milvus configured in .env
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl \
  --mode real --retriever local --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --experiment pm8-local-smoke \
  --output outputs/bench-local
```

This runs the PM7 5-case smoke suite against curated local documents covering 5 domains: llm_agents, embeddings, fine_tuning, reasoning, and rag.

**Why local corpus?** Real-time Tavily/MiMo search costs per query and is not reproducible across runs. The local corpus provides deterministic retrieval for stable metric comparison.

**Smoke config** (`examples/configs/benchmark_smoke.toml`) limits:
- 2 queries per task, 5 docs, 15 chunks
- 20 max LLM calls per run, 0 replans, 1 red-blue round
- 90s task timeout, 600s global timeout

Remove `--config examples/configs/benchmark_smoke.toml` to use default settings (higher cost, longer runtime).

PM8 accepted local-corpus result:

| Metric | Value |
|--------|-------|
| cases | 5 |
| avg_task_success_rate | 1.0 |
| avg_citation_coverage | 0.5297 |
| avg_factual_hit_rate | 1.0 |
| hallucination_flag_count | 0 |
| output | `outputs/bench-pm8-local-real-final/pm8-local-real-final/summary.json` |

Known follow-up: citation coverage is stable but still uneven across domains. The next optimization target is improving low-coverage cases such as embeddings and RAG without weakening citation rules.

## PM7 Smoke Benchmark（事实覆盖率校准）

PM7 将 `factual_hit_rate` 从粗糙字符串匹配升级为 fact-level 规则 + 可选 LLM 语义判定。5-case smoke 使用 `examples/bench/researchbench_smoke5.jsonl`，包含 dict 格式的 `expected_facts`（含 `keywords` / `aliases`）。

Benchmark runner 会在每个 case 完成后增量写出 `results.jsonl` 和 `summary.json`。长时间真实 run 如果中断，已完成 case 的 benchmark 级结果仍会保留。

### 运行命令

```bash
# 离线 mock 模式（验证 pipeline 端到端）
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode mock --output outputs/bench-pm7-mock

# 真实模式
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode real --output outputs/bench-pm7-smoke --experiment pm7-smoke

# 推荐：真实模型 + 本地 corpus
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode real --retriever local --corpus examples/corpus --output outputs/bench-local --experiment pm8-local-smoke
```

真实模式运行前必须先通过：

```bash
uv run deepresearch doctor --real
```

如果 Milvus check 失败并提示无法连接 `localhost:19530`，先启动 Docker Milvus Standalone：

```bash
docker compose -f docker-compose.milvus.yml up -d
```

### 预期改进

| 指标 | PM6（旧） | PM7 预期 |
|------|----------|---------|
| factual_hit_rate | 0.0 | 0.3–0.7 |
| fact_details | 无 | 每条 fact 有 hit/miss + reason |

### 当前结论

PM7 已证明 fact-level evaluator 可以解释真实报告，但实时搜索不是稳定评测基础设施：

- MiMo Search 会产生额外成本。
- Tavily 免费额度会耗尽，真实 run 中已出现 HTTP 432。
- 搜索结果不稳定会干扰 evidence extraction 和 citation coverage 的定位。

因此 PM8 改为 Local Corpus 可复现真实评测：先稳定资料输入和证据抽取，再把联网搜索作为 optional 增强层。

### 查看 fact_details

```bash
# 单条 case 的 fact 详情
uv run python -c "
import json
with open('outputs/bench-pm7-smoke/results.jsonl') as f:
    for line in f:
        r = json.loads(line)
        for d in r['evaluation'].get('fact_details', []):
            print(f\"{r['case_id']}: {d['fact'][:60]} -> {'HIT' if d['matched'] else 'MISS'} ({d['reason'][:60]})\")"
```

### fact_details 字段说明

| 字段 | 含义 |
|------|------|
| `fact` | 原始 expected fact 文本 |
| `matched` | 是否命中 (bool) |
| `matched_keywords` | 命中的关键词列表 |
| `unmatched_keywords` | 未命中的关键词列表 |
| `reason` | 命中/未命中原因（规则或 judge 判定） |
| `source` | `"rule"`（本地规则）或 `"judge"`（LLM 语义判定） |
| `supporting_evidence_ids` | 支持该 fact 的 evidence IDs（仅 judge 模式） |

### 匹配规则

1. 完整短语子串匹配 → 直接命中
2. 原始 token 覆盖率 ≥ 50% → 命中
3. 展开关键词（含缩写扩展和 aliases）覆盖率 ≥ 50% → 命中
4. 以上均未命中 → 标记 miss，如有 LLM 可选语义判定
