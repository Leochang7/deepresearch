# Langfuse Evaluation Plan

本文档定义 PM6 之后的评测与实验路线。结论：不在本项目内自研完整评测平台，改为使用 Langfuse 承担 tracing、dataset、experiment run、score 记录和可视化对比；本仓库只保留可复现的数据集、runner、指标计算器和上报 adapter。

## 1. 目标

PM6 的目标不是一次性实现“ResearchBench 11 领域 / 35 题 + HotpotQA 变体 + 统计显著性 + dashboard”的完整体系，而是先建立可复现的评测闭环：

```text
Benchmark Dataset -> deepresearch run -> local metrics -> Langfuse trace/score -> compare experiments
```

必须做到：

- 每个 benchmark case 可独立复现。
- 每次 run 的输入、配置、trace、报告、规则指标和 judge 分数可追踪。
- 本地离线测试仍不依赖 Langfuse。
- Langfuse 不替代核心 evaluator，只作为观测、记录和对比平台。

## 2. 职责边界

### 本项目负责

- Benchmark dataset schema。
- ResearchBench mini JSONL。
- Benchmark runner CLI。
- 本地规则指标：
  - `task_success_rate`
  - `citation_coverage`
  - `empty_citation_rate`
  - `report_section_completeness`
  - `factual_hit_rate`
  - `hallucination_flag`
- LLM-as-Judge schema 和调用封装。
- Langfuse adapter。
- 可复现实验脚本。

### Langfuse 负责

- Trace 可视化。
- Dataset 管理。
- Experiment run 记录。
- Score 记录。
- 不同模型、检索策略、prompt 版本的横向对比。
- Runtime prompt 版本、label 和发布管理（PM10 已完成）。
- 人工 review 和标注入口。

## 3. 分阶段实现

### PM6A：Langfuse 接入

- 增加可选依赖或 adapter，不影响默认离线测试。
- 配置项：
  - `DEEPRESEARCH_LANGFUSE_ENABLED`
  - `LANGFUSE_PUBLIC_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `LANGFUSE_HOST`
  - `DEEPRESEARCH_EXPERIMENT_NAME`
- 将 run 级输入、配置摘要、报告、evaluation、budget、trace 摘要上报到 Langfuse。
- Langfuse 不可用时只记录 warning，不影响本地 run。

### PM6B：ResearchBench mini

- 先做 10-15 题，不做 35 题。
- 存放路径：`examples/bench/researchbench_mini.jsonl`。
- 每题字段：

```json
{
  "id": "rbm_001",
  "domain": "ai",
  "difficulty": "medium",
  "question": "...",
  "expected_facts": ["...", "..."],
  "required_citations": true,
  "tags": ["multi-hop", "recent"]
}
```

### PM6C：Benchmark Runner

CLI：

```bash
uv run deepresearch benchmark --dataset examples/bench/researchbench_mini.jsonl --mode mock
uv run deepresearch benchmark --dataset examples/bench/researchbench_mini.jsonl --mode real --experiment pm6-mimo-baseline
```

输出：

- `outputs/bench/<experiment_id>/results.jsonl`
- `outputs/bench/<experiment_id>/summary.json`
- 可选上报 Langfuse。

### PM6D：LLM-as-Judge

先做结构化 5 维评分，不急着做统计显著性：

- factuality
- citation_support
- completeness
- reasoning_consistency
- readability

Judge 输出必须是 JSON，并复用现有 JSON fallback。

### PM6E：扩展完整评测

当 pipeline 稳定后再做：

- ResearchBench 扩到 11 领域 / 35 题。
- HotpotQA 深度研究变体。
- Bootstrap 95% CI。
- Cohen's d。
- MiMo / DeepSeek / vLLM / OpenAI 多后端对比。
- 6 项一键实验脚本。

### PM10：Prompt Management（已完成）

Prompt Management 的目标是让 Langfuse 管理所有 runtime prompts，同时保留本地 prompt 文件作为离线 fallback、测试基线和 bootstrap seed。

架构：

```text
PromptProvider
├── LocalPromptProvider        # 读 src/deepresearch/prompts/*.md
├── LangfusePromptProvider     # 从 Langfuse 拉 production/staging/dev label
└── FallbackPromptProvider     # Langfuse 失败时回退 local
```

迁移结果：

- Agent 和 judge 不再直接读取 `_PROMPT_PATH.read_text(...)`。
- 统一使用 `prompt_provider.get("planner")`、`get("researcher")`、`get("synthesizer")` 等稳定名称。
- Langfuse 中 prompt 使用 `deepresearch/<prompt_name>` 命名。
- 默认 provider 为 `local`，默认测试不依赖 Langfuse。
- 严格 `langfuse` provider 获取失败或返回空 prompt 时快速失败。
- `langfuse_with_local_fallback` 获取失败时回退本地 prompt。

配置：

```toml
[langfuse]
enabled = false
prompt_provider = "local"
prompt_label = "production"
```

CLI：

```bash
uv run deepresearch prompts push --label staging
uv run deepresearch run "..." --mode real --prompt-provider langfuse
```

验收标准：

- 默认 `uv run pytest` 无 Langfuse key、无网络也能通过。
- 本地 prompt 文件仍完整保留。
- 开启 Langfuse provider 时，runtime prompt 可按 label 获取。
- 远程 prompt 获取失败时，`langfuse_with_local_fallback` 能回退到本地 prompt。
- Langfuse trace 能记录 prompt 名称、label/version 和实验配置摘要。

## 4. 非目标

PM6 初期不做：

- 自研 dashboard。
- 自研 dataset UI。
- 自研 experiment tracking 后端。
- 大规模统计显著性。
- 论文级 benchmark 完整复刻。

这些能力优先交给 Langfuse 或放到 PM6E。

## 5. 验收标准

PM6A-PM6C 完成后，应满足：

- 默认 `uv run pytest` 无 Langfuse key 也能通过。
- `benchmark --mode mock` 可离线跑完整 mini dataset。
- 真实模式 benchmark 需要显式开启，并使用 `integration` / `llm` / `network` marker 测试。
- 每个 benchmark case 的结果能关联到 run_id、report、evaluation、trace summary。
- 开启 Langfuse 时，能在 Langfuse 中看到 experiment、trace 和 score。
