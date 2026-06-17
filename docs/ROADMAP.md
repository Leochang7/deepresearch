# Roadmap

本文件是项目路线图的唯一维护入口。历史 MVP 范围、Post-MVP 细节和早期实现计划已经归档到 `docs/archive/`，当前执行状态以 `TASKS.md` 为准，当前项目摘要以 `PROJECT_STATUS.md` 为准。

## 当前阶段

MVP、PM0-PM19 已完成。系统已经跑通：

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

## 当前完成：PM16-PM19 完整评测体系

PM16-PM19 已经把 benchmark 能力扩展成可复现实验平台。当前稳定评测主线是 local corpus，不依赖 UI 或联网搜索；Langfuse 作为 prompt、trace、score 和 experiment 可视化层。

完成项：

- PM16 Evaluation Dataset Suite：ResearchBench full、HotpotQA deep-research 变体、dataset manifest 和质量检查。
- PM17 Three-layer Evaluation Pipeline：规则指标、LLM-as-Judge 5 维评分、Bootstrap 95% CI、Cohen's d、Langfuse score/metadata 对齐。
- PM18 LLM Backend Matrix：DeepSeek、MiMo、OpenAI-compatible/vLLM 后端热切换和按模型分组的 benchmark summary。
- PM19 One-command Experiment Scripts：local mock、模型对比、prompt label 对比、multilingual 回归和 full suite 汇总脚本，生成 `suite_summary.json` 和 `comparison.json`。
- 验证：默认离线测试通过，最新记录为 `579 passed, 1 skipped`，ruff clean。

## 后续方向

### Release hardening

核心功能已经足够完整。下一阶段优先把现有能力跑稳、解释清楚、准备交付。任务状态和验收标准以 `docs/TASKS.md` 为准。

重点：

- 跑真实 local-corpus full suite，核对 `suite_summary.json`、`comparison.json`、Langfuse traces/scores 和本地产物。
- 清理 release notes、文档索引和示例命令，准备 push/PR/tag。
- 对低 citation coverage case 做定向质量优化，优先区分 evidence 抽取不足、Synthesizer 引用遗漏和 Evaluator 判定过严。

原则：

- Langfuse 作为 prompt/trace/score/experiment 可视化层，不替代本地 dataset、runner、metrics 和统计分析。
- 默认测试继续离线可跑；真实 LLM、Langfuse、Milvus、联网搜索都必须显式启用。
- 实验脚本只做 `deepresearch benchmark` 薄封装，不复制业务逻辑。

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
- PM11-PM15：并行 benchmark、中英跨语言检索/引用质量、multilingual benchmark、larger multilingual benchmark。
- PM16：ResearchBench full、HotpotQA deep-research variant、dataset manifest 和 validator。
- PM17：三层评测流水线、扩展规则指标、统计上下文和 Langfuse score/metadata 对齐。
- PM18：MiMo、DeepSeek、OpenAI-compatible/vLLM backend matrix 和模型分组 benchmark summary。
- PM19：一键实验脚本、suite artifacts、失败隔离和 full suite 汇总。

## 历史文档

历史路线和早期实现计划已归档：

- `archive/MVP_AND_ROADMAP.md`
- `archive/POST_MVP_ROADMAP.md`
- `archive/IMPLEMENTATION_PLAN.md`
