# Roadmap

本文件是项目路线图的唯一维护入口。历史 MVP 范围、Post-MVP 细节和早期实现计划已经归档到 `docs/archive/`，当前执行状态以 `TASKS.md` 为准，当前项目摘要以 `PROJECT_STATUS.md` 为准。

## 当前阶段

MVP、PM0-PM15 已完成。系统已经跑通：

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

## 当前完成：PM15 Larger Multilingual Benchmark

PM15 将 multilingual benchmark 扩成可复现的 20-case 单文件数据集，并新增 combined language-scenario breakdown。当前稳定评测主线是 local corpus，不依赖 UI、联网搜索或 Langfuse。

完成项：

- PM150：新增 `examples/bench/multilingual_large20.jsonl`，覆盖 5 English + 15 cross-lingual cases。
- PM151：benchmark summary 增加 `per_language_scenario`，按 `question_lang->evidence_lang` 分组。
- PM152：更新 PM15 复现文档，并补 large20 dataset 和 smoke sample 测试。
- 验证：`uv run pytest tests/evaluation/test_benchmark.py` 通过，相关 ruff 检查通过。

PM9-PM14 引用、多语言检索和 multilingual benchmark 已完成。后续如继续优化质量，优先分析 `multilingual_large20` 中 `per_language_scenario` 和低 citation coverage case，区分 evidence 抽取不足、Synthesizer 引用遗漏和 Evaluator 判定过严。

## 后续方向

### PM12 Cross-lingual Retrieval Quality

在 local corpus 和真实资料检索中引入跨语言混合检索。目标不是拆成中文/英文两套系统，而是让同一套 Retriever 能处理中文问题、英文资料、中文资料和中英混合资料，并能诊断召回失败来自哪里。

重点：

- Milvus vector search + BM25/keyword index 混合检索。
- 中文 query rewrite 和英文术语扩展，例如“检索增强生成” ↔ `RAG` / `retrieval-augmented generation`。
- 中英术语别名表和 query-time expansion。
- document-level RRF、chunk-level RRF、MMR context selection 保持统一融合。
- 评测按 `zh_question`、`en_question`、`zh_question_en_evidence`、`mixed_evidence` 等场景分组。

验收：

- 本地双语 corpus 中，中文问题可召回中文和英文 evidence。
- 英文问题不因中文扩展降低现有召回质量。
- citation coverage 和 factual hit 按语言场景输出 breakdown。

### PM13 Multilingual Evidence & Citation Quality

PM13 聚焦 evidence 抽取、quote matching、citation enforcement 和 synthesis 在多语言场景下的可审计性。重点是解决中文无空格、标点全半角、句界不稳定、术语翻译导致的引用覆盖误判。

重点：

- 中文/英文统一 quote normalization：大小写、标点、全半角、空白和常见术语变体。
- Evidence quality checker 支持跨语言 claim/quote 软匹配，但不能放松到接受无根据 claim。
- Synthesizer prompt 支持按用户问题语言输出，同时保留引用格式稳定。
- Evaluator 对中文事实、英文事实和跨语言事实分别给出 failure reason。

验收：

- 中文报告 citation coverage 不因分词和标点问题系统性低估。
- 英文报告保持现有引用检查行为。
- 多语言 case 的 unsupported claim 能被 Red/Evaluator 捕捉。

### PM14 Multilingual Benchmark

PM14 建立中英和跨语言 benchmark，用来证明 PM12/PM13 的检索、引用和事实指标确实提升。benchmark 不追求一开始做大，而是先覆盖关键失败模式。

重点：

- 新增 10-15 个 multilingual benchmark case。
- 每个 case 标注 question language、expected answer language、evidence language、domain、difficulty、expected facts、required citations。
- summary 输出 language/evidence-language breakdown。
- 保留 local-corpus 可复现路径，默认测试离线可跑。

验收：

- `uv run deepresearch benchmark ... --retriever local --corpus examples/corpus` 可跑 multilingual set。
- 输出按语言场景分组的 task success、citation coverage、factual hit 和 hallucination flag。
- PM12/PM13 前后指标可横向对比。

### PM15 Larger Benchmark

PM15 已完成 Larger Multilingual Benchmark，不引入 UI 和联网依赖。PM14 的 15-case 分散 smoke 已扩成一个可复现的 20-case 单文件数据集，并补 combined language-scenario breakdown，便于比较中文问题、英文问题、混合问题与不同 evidence 语言组合下的指标变化。

重点：

- `examples/bench/multilingual_large20.jsonl` 覆盖 5 个英文 smoke case + 15 个中英/跨语言 case。
- 模型压缩、隐私、多模态、DAG 编排、数据质量 5 个领域和对应本地 corpus 已补齐。
- summary 增加 `per_language_scenario`，例如 `zh->mixed`、`mixed->en`、`en->zh`。
- 默认测试离线可跑，真实评测仍走 local corpus + 显式 real mode。

后置到 PM16+：

- ResearchBench 35 题。
- HotpotQA 深度研究变体。
- 多后端对比实验。

### PM16 Network Retrieval Hardening

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
