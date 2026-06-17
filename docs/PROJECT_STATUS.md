# Project Status

DeepResearch Agent — 面向复杂深度研究任务的多智能体协作系统。

## 当前状态

MVP、PM0-PM19 已完成。PM7 的事实级 benchmark 评测能力已完成；PM8 将稳定验收路径切换为 Local Corpus；PM9 完成 local-corpus smoke citation coverage 优化；PM10 完成 PromptProvider 与 Langfuse Prompt Management；PM11-PM15 完成并行 benchmark、中英跨语言检索/引用质量、multilingual benchmark 和 20-case large benchmark；PM16-PM19 完成 dataset suite、三层评测流水线、LLM backend matrix 和一键实验脚本。PM20 已开始检索/记忆 hardening，当前已收敛公共词法、向量相似度和文档 identity 规则，下一步是可配置 LexicalPolicy + jieba tokenizer。

## 已完成能力

### 核心 Pipeline
- **Planner Agent**: 将复杂问题分解为 DAG 子任务，支持 replan 闭环（最多 N 轮）
- **Research Agent**: per-query 检索 → fetch → chunk → embedding → Milvus → RRF 融合 → rerank → MMR 选择 → evidence 提取
- **Synthesizer**: 将 evidence 合成为带引用的 Markdown 报告，支持 5 种 report profile
- **Red-Blue Review**: Red Agent 发现问题 → Blue Agent 修复 → Judge 评分，最多 3 轮
- **Evaluator**: 9 个核心指标（task_success_rate, citation_coverage, empty_citation_rate, report_section_completeness, factual_hit_rate, hallucination_flag, red/blue counts, judge_scores）+ fact-level 明细（fact_details, fact_coverage_distribution, per_fact_failure_reasons）

### 检索质量
- 多 query 并行检索 + document-level RRF 融合（rrf_k=60）
- 多 embedding query + chunk-level RRF + keyword recall 融合
- MMR 多样性选择（mmr_lambda=0.7, max 12 chunks）
- LocalDatasetRetriever、Memory keyword search、dedup/RRF 共用公共 lexical/cosine/document identity helper
- Evidence 质量门控：置信度过滤、quote 原文验证、claim-quote 语义一致性

### 模型支持
- LLM: MiMo v2.5 Pro（默认）+ DeepSeek + OpenAI-compatible/vLLM backend matrix
- Embedding: Qwen3-Embedding-4B（2560 维，OpenAI-compatible）
- Reranker: bge-reranker-v2-m3（OpenAI-compatible）
- 向量库: Milvus Standalone

### 配置与工程
- CLI: `run`, `init`, `index-corpus`, `eval`, `inspect --timeline`, `config`, `doctor`, `benchmark`
- 配置优先级: CLI > file > env > default
- Budget 追踪: LLM calls, search, fetch, chunks, embedding, rerank, elapsed time
- Langfuse 可选集成（无 key 时自动 no-op）
- PromptProvider: local / langfuse / langfuse_with_local_fallback，支持 prompt push bootstrap
- 完整 trace（JSONL）+ memory snapshot 导出

### 评测闭环
- ResearchBench mini: 12 个 benchmark case，覆盖 10 个领域
- ResearchBench full: 32 个 case，覆盖 12 个领域
- HotpotQA deep-research variant: 8 个 multi-hop case
- Benchmark runner: `deepresearch benchmark <dataset> --mode mock|real`
- Multilingual large benchmark: `examples/bench/multilingual_large20.jsonl`，20 个中英/跨语言 case
- Fact-level judge: 规则匹配 + 可选 LLM semantic verdict，输出每条事实命中/遗漏/幻觉原因
- 统计分析: per-domain/difficulty/language/language-scenario 分组、Bootstrap 95% CI、Cohen's d
- LLM-as-Judge 5 维评分: factuality, citation_support, completeness, reasoning_consistency, readability
- Experiment scripts: local mock、model compare、prompt ablation、multilingual regression、full suite，输出 `suite_summary.json` 和 `comparison.json`
- 冲突检测: same_source_different_claim, opposite_conclusion, contradictory_value

## MVP / PM 状态

| 阶段 | 状态 | 描述 |
|------|------|------|
| M0–M9 | ✅ 完成 | MVP 核心 pipeline（Planner → Research → Synthesize → Red-Blue → Evaluate） |
| PM0 | ✅ 完成 | 真实环境自检（doctor）+ integration 测试入口 + Milvus ORM 迁移 |
| PM1 | ✅ 完成 | 检索质量增强（RRF document/chunk 融合 + MMR 多样性选择） |
| PM2 | ✅ 完成 | 引用与证据质量（References 增强 + unsupported_citation + 质量门控 + report profile） |
| PM3 | ✅ 完成 | Replan 闭环 + RunBudget 统计 |
| PM4 | ✅ 完成 | inspect --timeline + MVP 验收文档 |
| PM5 | ✅ 完成 | Memory schema version + 轻量冲突检测 |
| PM6 | ✅ 完成 | Langfuse 集成 + ResearchBench mini + benchmark runner + LLM-as-Judge + 统计分析 |
| PM7 | 部分完成 | 事实级 benchmark 评测、5-case smoke dataset、失败原因分析已完成；联网 smoke 因 MiMo Search 计费和 Tavily 额度/432 不再作为主线 |
| PM8 | ✅ 完成 | Local Corpus 可复现真实评测：真实模型 + 真实 Milvus + 本地资料集，5-case smoke 跑通且无 hallucination flag |
| PM9 | ✅ 完成 | PM086 优化 citation coverage：模糊 quote 匹配、fallback evidence 放宽、引用提示增强和非事实过渡句保留 |
| PM10 | ✅ 完成 | Langfuse Prompt Management：统一 PromptProvider、Langfuse strict/fallback provider、prompt push CLI、run/benchmark provider override |
| PM11 | ✅ 完成 | 并行 benchmark runner：受限并发、case 隔离、确定性汇总和失败隔离 |
| PM12 | ✅ 完成 | Cross-lingual Retrieval Quality：CJK tokenization、中英 query expansion、语言 breakdown |
| PM13 | ✅ 完成 | Multilingual Evidence & Citation Quality：CJK claim/quote/fact matching 与语言 failure reason |
| PM14 | ✅ 完成 | Multilingual Benchmark：15-case 中英 local-corpus benchmark 和 summary comparison |
| PM15 | ✅ 完成 | Larger Multilingual Benchmark：20-case 单文件数据集和 `per_language_scenario` breakdown |
| PM16 | ✅ 完成 | Evaluation Dataset Suite：ResearchBench full、HotpotQA deep-research 变体、dataset manifest 和质量检查 |
| PM17 | ✅ 完成 | Three-layer Evaluation Pipeline：规则指标、LLM-as-Judge、统计上下文和 Langfuse score/metadata 对齐 |
| PM18 | ✅ 完成 | LLM Backend Matrix：MiMo、DeepSeek、OpenAI-compatible/vLLM 热切换和模型分组汇总 |
| PM19 | ✅ 完成 | One-command Experiment Scripts：local mock、模型对比、prompt ablation、multilingual 和 full suite 汇总脚本 |
| PM20 | 进行中 | Retrieval & Memory Hardening：已收敛公共词法/相似度/document key；下一步接入可配置 LexicalPolicy 与 jieba |

## 真实环境运行

### 前置条件

```bash
# 1. 启动 Milvus Standalone
docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API keys

# 3. 验证环境
uv run deepresearch doctor --real
```

### 运行单次研究

```bash
uv run deepresearch run "分析 2024-2026 年开源 LLM Agent 框架的发展趋势" --mode real
```

### 运行 Benchmark（含 Langfuse 上报）

```bash
# 启用 Langfuse
export DEEPRESEARCH_LANGFUSE_ENABLED=true
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...

# 运行 benchmark
uv run deepresearch benchmark examples/bench/researchbench_mini.jsonl --mode real --output outputs/bench-real

# PM8 local-corpus smoke
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode real --retriever local --corpus examples/corpus --config examples/configs/benchmark_smoke.toml --output outputs/bench-local --experiment pm8-local-smoke
```

产出:
- `outputs/bench-real/results.jsonl` — 每个 case 的详细结果
- `outputs/bench-real/summary.json` — 汇总指标（含 bootstrap CI、per-domain/difficulty 分组）
- `outputs/bench-real/<case-id>/` — 每个 case 的 report/evaluation/trace/memory_snapshot
- Langfuse dashboard 上的 experiment traces

PM8 验收结果：

- Output: `outputs/bench-pm8-local-real-final/pm8-local-real-final/summary.json`
- Cases: 5
- `avg_task_success_rate = 1.0`
- `avg_citation_coverage = 0.5297`
- `avg_factual_hit_rate = 1.0`
- `hallucination_flag_count = 0`

### 离线测试

```bash
uv run pytest           # 全量离线测试（584 passed, 1 skipped）
uv run ruff check .     # lint
```

## 已知限制

- **检索质量**: Tavily 结果偏向英文；中文查询已通过本地跨语言资料集优化，但联网搜索质量仍受 provider 影响；当前 builtin CJK unigram/bigram 保证离线稳定，PM201 计划接入可配置 jieba tokenizer
- **联网搜索成本/额度**: MiMo 原生搜索计费，Tavily 免费额度有限且可能返回 HTTP 432；benchmark 主路径改为 Local Corpus
- **LLM 幻觉**: Synthesizer 可能生成"通过引用检查但过度解读 evidence"的 claim
- **Milvus Standalone 必需**: 不支持 Milvus Lite（嵌入式）；需要 Docker 或 standalone 部署
- **PM7 联网 smoke 不稳定**: 实时搜索导致成本、额度、排序和网络波动，不适合作为稳定验收路径
- **单轮执行**: 无交互式 refinement；pipeline 一次跑完
- **真实 large benchmark 成本**: `multilingual_large20` 真实模式会调用真实 LLM/embedding/reranker/Milvus；默认测试只跑 mock sample
- **Langfuse 可选**: 评测追踪默认 no-op；严格 prompt provider 需要 Langfuse SDK 和密钥，fallback provider 可回退本地 prompt

## 下一阶段方向

核心工程主线已经闭环。下一步不建议继续堆大功能，优先做 release hardening 和真实验收：

- 跑一次真实 local-corpus full suite，确认 `suite_summary.json`、`comparison.json`、Langfuse traces/scores 和本地产物一致。
- 接入可配置 LexicalPolicy 与 jieba tokenizer，让中文 BM25/keyword recall 更干净，同时保留 builtin fallback。
- 清理文档和 release notes，准备 push/PR/tag。
- 如果继续优化质量，优先分析 `multilingual_large20` 和 `researchbench_full` 的低 citation coverage case，而不是新增 UI。

## 仓库结构

```
src/deepresearch/
├── agents/          # planner, researcher, synthesizer, red/blue agent, judge, evidence_quality
├── core/            # dag, executor, run_manager, budget, trace, json_repair, state
├── embeddings/      # base, mock, openai_compatible
├── evaluation/      # metrics, benchmark, judge_eval, langfuse
├── llm/             # base, mock, mimo, deepseek, openai_compatible
├── memory/          # store, milvus_store, conflict
├── prompts/         # prompt templates and PromptProvider implementations
├── rerankers/       # base, mock, openai_compatible
├── retrieval/       # base, mock, tavily, mimo, local_dataset, fetcher, chunking, dedup, fusion
├── schemas/         # task, evidence, report, evaluation
├── cli.py
├── config.py
└── doctor.py

tests/               # 584 passed, 1 skipped, 100% 离线可跑
examples/
├── bench/           # researchbench_mini.jsonl, researchbench_smoke5.jsonl, multilingual_large20.jsonl
└── corpus/          # 本地资料集示例
docs/                # PRD, MVP plan, configuration, post-MVP roadmap, acceptance
```
