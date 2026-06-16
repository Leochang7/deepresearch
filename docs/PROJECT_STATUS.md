# Project Status

DeepResearch Agent — 面向复杂深度研究任务的多智能体协作系统。

## 当前状态

MVP 和 PM0-PM6 已完成。PM7 的事实级 benchmark 评测能力已完成并通过离线验证；真实联网 smoke 已暴露搜索成本和额度问题，下一阶段改为 PM8 Local Corpus 可复现真实评测。

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
- Evidence 质量门控：置信度过滤、quote 原文验证、claim-quote 语义一致性

### 模型支持
- LLM: MiMo v2.5 Pro（默认）+ DeepSeek fallback
- Embedding: Qwen3-Embedding-4B（2560 维，OpenAI-compatible）
- Reranker: bge-reranker-v2-m3（OpenAI-compatible）
- 向量库: Milvus Standalone

### 配置与工程
- CLI: `run`, `init`, `index-corpus`, `eval`, `inspect --timeline`, `config`, `doctor`, `benchmark`
- 配置优先级: CLI > file > env > default
- Budget 追踪: LLM calls, search, fetch, chunks, embedding, rerank, elapsed time
- Langfuse 可选集成（无 key 时自动 no-op）
- 完整 trace（JSONL）+ memory snapshot 导出

### 评测闭环
- ResearchBench mini: 12 个 benchmark case，覆盖 10 个领域
- Benchmark runner: `deepresearch benchmark <dataset> --mode mock|real`
- Fact-level judge: 规则匹配 + 可选 LLM semantic verdict，输出每条事实命中/遗漏/幻觉原因
- 统计分析: per-domain/difficulty 分组、Bootstrap 95% CI、Cohen's d
- LLM-as-Judge 5 维评分: factuality, citation_support, completeness, reasoning_consistency, readability
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
| PM8 | 规划中 | Local Corpus 可复现真实评测：真实模型 + 真实 Milvus + 本地资料集，先稳定 evidence/citation 再接回联网搜索 |

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

# PM8 local-corpus smoke（PM8 实现 benchmark --corpus 后）
uv run deepresearch benchmark examples/bench/researchbench_smoke5.jsonl --mode real --retriever local --corpus examples/corpus --output outputs/bench-local --experiment pm8-local-smoke
```

产出:
- `outputs/bench-real/results.jsonl` — 每个 case 的详细结果
- `outputs/bench-real/summary.json` — 汇总指标（含 bootstrap CI、per-domain/difficulty 分组）
- `outputs/bench-real/<case-id>/` — 每个 case 的 report/evaluation/trace/memory_snapshot
- Langfuse dashboard 上的 experiment traces

### 离线测试

```bash
uv run pytest           # 全量离线测试（435 passed, 1 skipped）
uv run ruff check .     # lint
```

## 已知限制

- **检索质量**: Tavily 结果偏向英文；中文查询效果较差
- **联网搜索成本/额度**: MiMo 原生搜索计费，Tavily 免费额度有限且可能返回 HTTP 432；benchmark 主路径改为 Local Corpus
- **LLM 幻觉**: Synthesizer 可能生成"通过引用检查但过度解读 evidence"的 claim
- **Milvus Standalone 必需**: 不支持 Milvus Lite（嵌入式）；需要 Docker 或 standalone 部署
- **PM7 联网 smoke 不稳定**: 实时搜索导致成本、额度、排序和网络波动，不适合作为稳定验收路径
- **单轮执行**: 无交互式 refinement；pipeline 一次跑完
- **Benchmark 串行**: benchmark runner 顺序执行每个 case，无并行
- **Langfuse 可选**: 未安装 langfuse 包时自动降级为 no-op，不影响核心功能

## 下一阶段方向

- **PM8 Local Corpus smoke**: 准备可提交本地资料集，跑 `researchbench_smoke5` 的真实模型 + 本地 corpus benchmark
- **并行 benchmark**: benchmark runner 支持 asyncio.gather 并发执行多个 case
- **Hybrid retrieval**: Milvus vector search + BM25 keyword search 混合检索
- **Interactive mode**: 支持用户在 synthesis 前审查 evidence 并提供反馈
- **多语言优化**: 中文查询的专用检索策略和 prompt 优化
- **更大规模 benchmark**: ResearchBench 35 题 + HotpotQA 深度研究变体

## 仓库结构

```
src/deepresearch/
├── agents/          # planner, researcher, synthesizer, red/blue agent, judge, evidence_quality
├── core/            # dag, executor, run_manager, budget, trace, json_repair, state
├── embeddings/      # base, mock, openai_compatible
├── evaluation/      # metrics, benchmark, judge_eval, langfuse
├── llm/             # base, mock, mimo, deepseek
├── memory/          # store, milvus_store, conflict
├── prompts/         # planner, researcher, synthesizer, red/blue, judge_eval
├── rerankers/       # base, mock, openai_compatible
├── retrieval/       # base, mock, tavily, mimo, local_dataset, fetcher, chunking, dedup, fusion
├── schemas/         # task, evidence, report, evaluation
├── cli.py
├── config.py
└── doctor.py

tests/               # 435 passed, 1 skipped, 100% 离线可跑
examples/
├── bench/           # researchbench_mini.jsonl (12 cases), researchbench_smoke5.jsonl (5 cases)
└── corpus/          # 本地资料集示例
docs/                # PRD, MVP plan, configuration, post-MVP roadmap, acceptance
```
