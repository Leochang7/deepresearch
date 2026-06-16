# Roadmap

本文件是项目路线图的唯一维护入口。历史 MVP 范围、Post-MVP 细节和早期实现计划已经归档到 `docs/archive/`，当前执行状态以 `TASKS.md` 为准，当前项目摘要以 `PROJECT_STATUS.md` 为准。

## 当前阶段

MVP、PM0-PM10 已完成。系统已经跑通：

```text
Planner -> DAG Executor -> Research Agent -> Retriever -> Memory -> Synthesizer -> Red/Blue/Judge -> Evaluator
```

当前稳定验收路径是 local corpus real benchmark：

```bash
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl \
  --mode real \
  --retriever local \
  --corpus examples/corpus \
  --config examples/configs/benchmark_smoke.toml \
  --output outputs/bench-local \
  --experiment pm8-local-smoke
```

PM8 5-case local-corpus real smoke 结果：

- `avg_task_success_rate = 1.0`
- `avg_citation_coverage = 0.5297`
- `avg_factual_hit_rate = 1.0`
- `hallucination_flag_count = 0`

## 当前完成：PM10 Langfuse Prompt Management

PM10 的目标是让 Langfuse 管理 runtime prompts，同时保留本地 prompt 文件作为离线 fallback、测试基线和 bootstrap seed。当前已完成 PromptProvider 抽象、Langfuse strict/fallback provider、prompt push CLI，以及 `run` / `benchmark` 的 provider override。

完成项：

- PM100：统一 PromptProvider，Agent/Judge 不再直接读取 prompt 文件。
- PM101：接入 `local`、`langfuse`、`langfuse_with_local_fallback` 三种 provider。
- PM102：增加 `uv run deepresearch prompts push --label staging`，并支持 `--prompt-provider`。
- PM103：Review 修复 strict/fallback 失败语义、CLI override 和 prompt push 失败处理。
- 验证：`uv run pytest tests/ -x -q` 通过，`uv run ruff check .` 通过。

PM9 引用覆盖率优化已完成，后续如继续优化引用质量，优先分析新 benchmark 输出中 coverage 仍低的 case，区分 evidence 抽取不足、Synthesizer 引用遗漏和 Evaluator 判定过严。

## 后续方向

### P1 并行 benchmark

当前 benchmark runner 顺序执行 case。后续可支持受限并发：

- 使用 `asyncio.gather` 并发多个 case。
- 保留 run 级 budget 和 case 级隔离。
- 默认并发数保守配置，避免真实模型和 Milvus 压力失控。

### P2 Hybrid retrieval

在 local corpus 和真实资料检索中引入更强的混合检索：

- Milvus vector search
- BM25 或轻量 keyword index
- document-level RRF
- chunk-level RRF
- MMR context selection

目标是提升 evidence recall，而不是只追求更多文档。

### P3 Interactive mode

增加用户在 synthesis 前审查 evidence 的能力：

- 展示每个 task 的候选 evidence。
- 允许用户确认、排除或补充资料。
- 将用户反馈写入 trace 和 memory。

### P4 多语言优化

针对中文研究任务优化检索和 prompt：

- 中文 query rewrite。
- 中英文别名和术语归一。
- 中文资料的 chunk、关键词召回和 citation 检查。

### P5 更大规模 benchmark

在 5-case local-corpus smoke 稳定后，再扩大评测规模：

- ResearchBench mini 完整 12 case。
- ResearchBench 35 题。
- HotpotQA 深度研究变体。
- Bootstrap 95% CI。
- Cohen's d。
- 多后端对比实验。

### P6 网络检索增强

Tavily 和 MiMo Search 保持 optional retriever adapter：

- 不作为默认 benchmark 主路径。
- 使用真实 API 额度时必须显式开启。
- 结果不可复现时不得作为稳定验收依据。

## 已完成里程碑摘要

- M0-M9：MVP 核心 pipeline、CLI、RunManager、mock smoke。
- PM0：`deepresearch doctor`、真实环境自检、MilvusClient 迁移。
- PM1：document/chunk RRF、MMR context selection。
- PM2：References 增强、unsupported citation 检查、evidence quality gate、report profile。
- PM3：真实 replan 闭环、run budget 统计。
- PM4：`inspect --timeline`、MVP 验收文档。
- PM5：Memory schema version、轻量冲突检测。
- PM6：Langfuse adapter、ResearchBench mini、benchmark runner、LLM-as-Judge。
- PM7：fact-level 规则指标、semantic judge、per-fact failure reason。
- PM8：local corpus 可复现真实评测，联网搜索降级为增强层。
- PM9：local-corpus smoke citation coverage 优化。
- PM10：Langfuse Prompt Management、PromptProvider、prompt push CLI。

## 历史文档

历史路线和早期实现计划已归档：

- `archive/MVP_AND_ROADMAP.md`
- `archive/POST_MVP_ROADMAP.md`
- `archive/IMPLEMENTATION_PLAN.md`
