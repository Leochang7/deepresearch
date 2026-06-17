# Release Hardening

本文件记录交付前真实验收、阻塞点和质量分析。当前本地离线测试仍以
`uv run pytest` 为准，真实验收只记录可复现命令、产物和已观察到的限制。

## 2026-06-17 真实环境检查

命令：

```bash
uv run deepresearch doctor --real
```

结果：

- LLM endpoint OK：`mimo / mimo-v2.5-pro`
- Embedding endpoint OK：`Qwen3-Embedding-4B`, dim `2560`
- Reranker endpoint OK：`bge-reranker-v2-m3`
- Langfuse endpoint OK：`http://localhost:4000/`, prompt label `production`, prompts `7`
- Milvus schema OK：`deepresearch_chunks` 和 `deepresearch_memories` 均为 dim `2560`
- Tavily 返回 HTTP 432，但 full suite 使用 `--retriever local`，不依赖 Tavily

## 真实 full suite 尝试

命令：

```bash
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl \
  --mode real \
  --retriever local \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --output outputs/experiments/release-hardening-real \
  --experiment researchbench_smoke5
```

观察：

- 工具窗口 15 分钟超时前完成 3 个 case，并在第 4 个 case 中途停止。
- 已完成产物位于 `outputs/experiments/release-hardening-real/researchbench_smoke5/`。
- 已完成 case：`rb-001`, `rb-003`, `rb-006`。
- 中断 case：`rb-009`，只有 `trace.jsonl`，没有最终 report/evaluation。

已完成 case 指标：

| case | task_success_rate | citation_coverage | hallucination_flag | elapsed_seconds | total_tokens |
|------|-------------------|-------------------|--------------------|-----------------|--------------|
| rb-001 | 1.0 | 0.7368 | false | 248.204 | 60500 |
| rb-003 | 1.0 | 0.9048 | false | 241.688 | 62241 |
| rb-006 | 1.0 | 0.5294 | false | 205.031 | 63371 |

结论：

- 真实 local-corpus pipeline 可以完成 case，且已完成 case 均无 hallucination flag。
- 串行 full suite 不适合在短交互窗口内运行；按当前耗时估算，43-case suite 需要数小时。
- `evaluation.json` 是 RunManager 通用评测，不带 benchmark expected_facts；因此单 case run artifact 中 `factual_hit_rate=0.0` 不是 benchmark 最终事实命中率。需要 benchmark 完整结束后看 `results.jsonl` 和 `summary.json`。

## Citation Coverage 初步分析

`rb-006` 的 citation coverage 为 `0.5294`，明显低于 `rb-001` 和 `rb-003`。
该 case 仍然 task success 为 `1.0` 且无 hallucination flag，说明主要问题不是检索失败，
而是生成报告中的部分分析句没有绑定 evidence citation。

优先排查顺序：

1. Synthesizer 是否在解释性/归纳性句子中遗漏引用。
2. Evaluator 是否把报告结构句或概括句误当 substantive claim。
3. Evidence extraction 是否提供了足够多、足够短的可引用 claim。

建议下一步使用 `rb-006` 作为定向优化 case，而不是先跑更大的真实 suite。

## 交付前行动项

- 使用后台终端或 CI runner 跑完整 real local-corpus suite，避免交互工具超时。
- 为 full suite 命令增加推荐 `--max-concurrency 2` 路径，并明确真实 endpoint rate limit 风险。
- 对 `rb-006` 做 citation coverage case review，定位 Synthesizer、Evaluator 或 evidence extraction 的责任边界。
- 保持 Tavily/联网搜索为 optional，不把 HTTP 432 作为 release blocker。
