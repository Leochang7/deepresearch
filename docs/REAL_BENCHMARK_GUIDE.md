# Real Benchmark Guide

## 完整真实 Benchmark + Langfuse 上报

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

### 2. 运行 Benchmark

```bash
uv run deepresearch benchmark \
  examples/bench/researchbench_mini.jsonl \
  --mode real \
  --output outputs/bench-$(date +%Y%m%d)
```

### 3. 查看结果

```bash
# 汇总指标
cat outputs/bench-*/summary.json | python -m json.tool

# 单个 case 详情
uv run deepresearch inspect <run-id> --timeline

# Langfuse dashboard
open https://cloud.langfuse.com
```

### 4. 归档报告样例

选择效果好的 run 归档：

```bash
RUN_ID=<best-run-id>

# 脱敏归档（去除 trace 全量和密钥）
cp outputs/$RUN_ID/report.md docs/examples/sample-report.md
cp outputs/$RUN_ID/evaluation.json docs/examples/sample-evaluation.json

# benchmark summary
cp outputs/bench-*/summary.json docs/examples/sample-bench-summary.json
```

### 5. 预期指标

| 指标 | 预期范围 |
|------|----------|
| task_success_rate | 0.8–1.0 |
| citation_coverage | 0.6–0.9 |
| factual_hit_rate | 0.5–0.8 |
| hallucination_flag_count | 0–3 |
| avg_elapsed_seconds | 30–120s |

### 6. 故障排查

```bash
# Milvus 连接失败
docker ps | grep milvus
curl http://localhost:19530/healthz

# LLM API 限流
# 检查 trace.jsonl 中的 error 字段

# Embedding 维度不匹配
uv run deepresearch doctor --real  # 会检查 dim
```

## PM7 Smoke Benchmark（事实覆盖率校准）

PM7 将 `factual_hit_rate` 从粗糙字符串匹配升级为 fact-level 规则 + 可选 LLM 语义判定。5-case smoke 使用 `examples/bench/researchbench_smoke5.jsonl`，包含 dict 格式的 `expected_facts`（含 `keywords` / `aliases`）。

### 运行命令

```bash
# 离线 mock 模式（验证 pipeline 端到端）
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode mock --output outputs/bench-pm7-mock

# 真实模式
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode real --output outputs/bench-pm7-smoke --experiment pm7-smoke
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
