# Roadmap

本文件是项目路线图的唯一维护入口。历史 MVP 范围、Post-MVP 细节和早期实现计划已经归档到 `docs/archive/`，当前执行状态以 `TASKS.md` 为准，当前项目摘要以 `PROJECT_STATUS.md` 为准。

## 当前阶段

MVP、PM0-PM26 已完成。系统已经跑通：

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

## 当前完成：PM16-PM26 完整评测、Langfuse Ops 与量化校准

PM16-PM26 已经把 benchmark 能力扩展成可复现实验平台，并把本地评测闭环映射到 Langfuse，同时建立可复现的量化 claims 口径。当前稳定评测主线是 local corpus，不依赖 UI 或联网搜索；Langfuse 作为 prompt、trace、score、experiment 和人工审阅协作层。

完成项：

- PM16 Evaluation Dataset Suite：ResearchBench full、HotpotQA deep-research 变体、dataset manifest 和质量检查。
- PM17 Three-layer Evaluation Pipeline：规则指标、LLM-as-Judge 5 维评分、Bootstrap 95% CI、Cohen's d、Langfuse score/metadata 对齐。
- PM18 LLM Backend Matrix：DeepSeek、MiMo、OpenAI-compatible/vLLM 后端热切换和按模型分组的 benchmark summary。
- PM19 One-command Experiment Scripts：local mock、模型对比、prompt label 对比、multilingual 回归和 full suite 汇总脚本，生成 `suite_summary.json` 和 `comparison.json`。
- PM20 Retrieval/Memory/Model Hardening：公共词法、jieba tokenizer、模型后端 factory 和 OpenAI-compatible client 收敛。
- PM21 Evaluation & Schema Hardening：typed EvaluationLayers/BenchmarkCase、fact matching 拆分和 Langfuse 上报边界收敛。
- PM22 Langfuse Dataset & Experiment Binding：dataset push、case trace metadata 和 benchmark scores。
- PM23 Fine-grained Langfuse DAG/Agent Observations：run/phase/task nested observations 和 budget scores。
- PM24 Langfuse-managed Evaluator & Prompt Versioning：runtime prompt name/version/hash metadata 和 judge prompt override。
- PM25 Human Annotation Queue & Review Loop：annotation candidate 标记和人工标注 JSONL 回流。当前 Langfuse SDK 无稳定 annotation queue item API，项目使用 trace-level `annotation_candidate` score 作为 handoff。
- PM26 Quantitative Claim Calibration：建立公开量化指标口径、本地 JSON repair fixture 和真实 ResearchBench full retrieval-only 对照评测。
- 验证：默认离线测试通过，最新记录为 `656 passed, 1 skipped`，ruff clean。

## 后续方向

### PM20 Retrieval & Memory Hardening

当前检索和记忆主线从“功能堆叠”转为“规则收敛和中文词法质量”。PM200 已将 LocalDatasetRetriever、Memory keyword search、RRF/MMR、dedup 和 Milvus adapter 里的公共 lexical/cosine/document identity 规则收敛到共享 helper，并让本地 corpus retrieve 在实例内缓存文档。

PM201 已接入可配置 `LexicalPolicy`：

- 默认 `builtin` tokenizer 继续使用 CJK unigram/bigram，保证 CI、mock、local benchmark 离线可复现。
- 可选 `jieba` tokenizer 用于中文 BM25/keyword recall，降低 CJK ngram 噪声。
- 仓库内维护 userdict，覆盖 RAG、LLM-as-Judge、Qwen、MiMo、DeepResearch 等项目术语。
- LocalDatasetRetriever、Memory keyword search、Evaluator token overlap 共享同一 policy，避免多套中文词法规则漂移。

PM202 已完成模型后端 hardening：

- MiMo/DeepSeek 保留对外类名，但内部作为 OpenAI-compatible 薄 wrapper，复用统一 chat client。
- `deepresearch.models` 提供 `build_llm_client`、`build_embedding_client` 和 `build_reranker_client`，CLI、doctor 和 index-corpus 共享同一装配路径。
- `doctor --real` 按当前 `llm.provider` 检查真实 LLM endpoint，不再固定检查 MiMo。
- 移除未实现自动 fallback 的 `fallback_provider` 活跃配置，避免误导真实运行配置。

### Langfuse Evaluation Ops

PM22-PM25 已完成，不再新增一套本地评测平台。当前原则是本地 JSONL、runner、metrics 和统计分析继续作为离线 source of truth，Langfuse 承担协作、可视化、prompt 管理和实验对比。

- 本地 benchmark dataset 可 bootstrap 到 Langfuse dataset items。
- Benchmark trace 通过 `dataset_name + case_id`、trace metadata 和 `benchmark_*` scores 关联。
- Planner、DAG task、retrieval、memory、synthesis、Red/Blue/Judge 和 Evaluator 已记录为 nested observations。
- Runtime prompt metadata 已覆盖 planner/researcher/synthesizer/red_agent/blue_agent/judge_eval/fact_judge。
- 人工审阅候选通过 trace-level `annotation_candidate` score 标记；人工标注结果通过本地 JSONL overlay 回流 summary。

### Release hardening

核心功能已经足够完整。下一阶段优先把现有能力跑稳、解释清楚、准备交付。任务状态和验收标准以 `docs/TASKS.md` 为准。

重点：

- 跑后台真实 local-corpus full suite，核对 `suite_summary.json`、`comparison.json`、Langfuse traces/scores 和本地产物。交互窗口内已完成 3 个真实 smoke case，详见 `RELEASE_HARDENING.md`。
- 清理 release notes、文档索引和示例命令，准备 push/PR/tag。
- 对低 citation coverage case 做定向质量优化，优先从 `rb-006` 开始区分 evidence 抽取不足、Synthesizer 引用遗漏和 Evaluator 判定过严。

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
- PM20：检索/记忆/模型装配 hardening。
- PM21：评测 schema hardening。
- PM22-PM25：Langfuse dataset binding、nested observations、prompt versioning 和 annotation review loop。
- PM26：量化 claims 校准和真实数据集 retrieval-only 对照评测。

## 历史文档

历史路线和早期实现计划已归档：

- `archive/MVP_AND_ROADMAP.md`
- `archive/POST_MVP_ROADMAP.md`
- `archive/IMPLEMENTATION_PLAN.md`
