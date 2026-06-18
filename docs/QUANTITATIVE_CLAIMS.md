# Quantitative Claims

本文件记录可公开引用的量化指标口径。所有数字必须能对应到可复现的本地对照评测或真实 benchmark。

## 生成命令

```bash
uv run python -m deepresearch.evaluation.retrieval_ablation examples/bench/researchbench_full.jsonl \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --embedding real \
  --top-k 5 \
  --output outputs/experiments/retrieval-ablation-researchbench-full-real/summary.json
```

输出文件位于 `outputs/experiments/retrieval-ablation-researchbench-full-real/summary.json`，不提交到仓库。

## 当前可用数字

| 指标 | 口径 | 结果 | 公开陈述建议 |
| --- | --- | --- | --- |
| fact recall@5 | ResearchBench full，32 case，真实 Qwen embedding，本地 corpus，retrieval-only | pure vector 95.8%，RRF hybrid 93.8%，RRF+MMR 93.8% | ResearchBench full retrieval-only 真测中 fact recall@5 达 95.8% |
| MMR 证据保真 | ResearchBench full，32 case，真实 Qwen embedding，本地 corpus，top5 来源多样性 | pure vector 73.8% → RRF+MMR 82.5% | MMR 将 top5 可追溯证据来源多样性 73.8% → 82.5% |
| JSON 结构化解析成功率 | JSON repair fixture，12 个 LLM 常见非严格 JSON 输出 | strict JSON 25.0% → fallback 91.7% | 结构化输出解析成功率在异常样例中 25.0% → 91.7% |

## 使用边界

- `fact recall@5` 和 `MMR` 来自真实 benchmark dataset + 真实 embedding 的 retrieval-only 测试，不跑 LLM，不等同于端到端报告质量。
- 当前 ResearchBench full 上 pure vector recall 已经很高，不能写成 RRF 提升 recall；RRF 只能作为融合链路能力描述。
- `JSON repair` 是本地 deterministic fixture，不等同于完整真实生产 benchmark。
- 对外引用这些数字时，应避免写成全量线上生产提升。
- 后续若完成完整真实 suite，应优先替换离线 fixture 数字。
