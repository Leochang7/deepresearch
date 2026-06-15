# MVP 范围与后续路线

## 1. MVP 定义

MVP 的目标不是做一个功能完备的深度研究平台，而是证明核心闭环成立：

> 输入复杂问题 -> 拆解任务 DAG -> 并发执行研究 -> 共享记忆沉淀证据 -> 合成报告 -> 对抗审查修复 -> 输出评测结果。

MVP 必须可运行、可展示、可复现。

## 2. MVP 用户故事

用户在命令行执行：

```bash
uv run deepresearch run "分析 2024-2026 年开源 LLM Agent 框架的发展趋势"
```

系统输出：

- `outputs/<run_id>/report.md`
- `outputs/<run_id>/trace.jsonl`
- `outputs/<run_id>/memory_snapshot.jsonl`
- `outputs/<run_id>/evaluation.json`

用户可以打开报告查看研究结论，也可以查看 trace 理解每个 Agent 做了什么。

## 3. MVP 功能范围

### 3.1 必须实现

- CLI 入口。
- 配置文件读取。
- Planner 生成 DAG 任务计划。
- DAG Executor 按依赖执行任务。
- Research Agent 生成子任务研究结果。
- Retriever 支持本地资料集、Tavily 真实 Web 搜索、MiMo 原生搜索和 mock 搜索后端。
- 使用 `httpx + trafilatura` 做轻量网页正文抓取。
- Milvus Lite 记忆库。
- MiMo v2.5 Pro 作为默认 Planner/Research/Synthesizer/Red-Blue/Judge 模型。
- Qwen3-Embedding-4B 作为 1024 维 embedding 模型。
- bge-reranker-v2-m32 作为 reranker。
- embedding 向量检索、标量过滤和关键词 fallback。
- Synthesizer 生成 Markdown 报告。
- Red Agent 审查报告。
- Blue Agent 修复报告。
- 基础 Evaluator 输出规则指标。
- 执行 trace 落盘。

### 3.2 可以简化

- 检索源可以先使用 Tavily、MiMo 原生搜索、手动 mock 数据或本地资料集。
- MCP 先作为后续适配层，不进入 MVP 必须范围。
- Milvus 部署先使用 Milvus Lite；MVP 不做分布式集群。
- DeepSeek 作为 fallback 后端保留。
- Red-Blue 先做 1-2 轮，不追求复杂多轮收敛。
- ResearchBench 最后再做；MVP 只保留 3 个 smoke demo 示例。

### 3.3 暂不实现

- Web UI。
- 多用户系统。
- 分布式任务队列。
- 权限系统。
- 大规模爬虫。
- 复杂可视化 dashboard。
- 完整论文级 benchmark。

## 4. MVP 成功标准

- 端到端运行时间在可控范围内，单个 demo 任务建议小于 10 分钟。
- 至少支持 3 个不同主题的示例研究任务。
- 任意一次运行都能生成 report、trace、memory、evaluation 四类产物。
- 故意让一个子任务失败时，系统能记录失败并继续合成报告。
- Red-Blue 修复后，引用覆盖率或结构完整度至少有一项提升。

## 5. MVP 之后的路线

### Phase 1：增强执行可靠性

- 完善 9 状态状态机。
- 增加任务级重试策略。
- 增加批量失败 replan。
- 增加全局超时强制合成。
- 增加 JSON 解析 fallback：
  - 严格 JSON 解析。
  - 从 Markdown 代码块提取 JSON。
  - 基于 schema 的字段修复。

### Phase 2：增强记忆与上下文压缩

- L1：embedding 粗过滤。
- L2：Milvus 标量过滤 + TextRank 或 MMR 做片段筛选。
- L3：保留关键原文证据。
- 写前去重。
- 基础矛盾检测。
- 记忆按 run、task、source、claim 分层组织。
- 从 Milvus Lite 演进到 Docker Milvus Standalone。

### Phase 2.5：增强资料获取能力

- 增加 `BrowserRetriever`，支持网页正文抓取、正文清洗、缓存和去重。
- 增加 `MCPRetriever`，用于接入 GitHub、论文库、数据库、文件系统等外部工具。
- 完善 `MiMoSearchRetriever`，用于接入 MiMo 原生搜索能力。
- 增加通用 `ModelNativeSearchRetriever`，用于接入其他模型厂商原生搜索能力，作为 fallback 或对比实验。
- 为每个 Retriever 增加统一 trace，记录 query、来源、耗时、返回数量和失败原因。

### Phase 3：增强 Red-Blue 对抗

- Red Agent 输出结构化问题清单。
- Blue Agent 根据问题类型选择修复动作。
- Judge 判断修复是否有效。
- 增加评分收敛检测。
- 增加震荡检测，避免来回修改同一问题。

### Phase 4：完善评测体系

- 自建 ResearchBench。
- 引入 HotpotQA 风格多跳问题。
- 规则指标扩展到事实覆盖、引用支持度、幻觉风险。
- LLM-as-Judge 五维评分。
- Bootstrap 95% 置信区间。
- Cohen's d 效应量。
- 一键实验脚本。

### Phase 5：产品化与展示

- 增加 Web UI 或 Gradio/Streamlit demo。
- 增加任务图可视化。
- 增加报告版本对比。
- 增加 Red-Blue 修复 diff。
- 增加 benchmark dashboard。

## 6. 推荐里程碑

### Week 1：项目骨架与 CLI

- 建立包结构。
- 完成配置系统。
- 完成 CLI 输入输出。
- 定义核心数据模型。

### Week 2：Planner 与 Executor

- 完成 DAG 数据结构。
- 完成状态机。
- 完成异步调度。
- 增加基础单元测试。

### Week 3：Research、Memory、Synthesis

- 完成 Research Agent。
- 完成 Retriever 接口、LocalDatasetRetriever、Tavily WebSearchRetriever、MiMoSearchRetriever 和 mock 搜索后端。
- 完成 `httpx + trafilatura` 正文抓取、chunk 和去重。
- 完成 Milvus collection schema、写入、检索和本地快照导出。
- 完成报告合成。
- 端到端跑通第一版。

### Week 4：Red-Blue 与 Evaluator

- 完成审查和修复闭环。
- 完成基础指标。
- 固化示例任务和输出。
- 整理 README 与 demo。
