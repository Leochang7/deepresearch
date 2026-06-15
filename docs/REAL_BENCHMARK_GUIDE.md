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
