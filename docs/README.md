# Documentation Guide

本文件是 `docs/` 的入口和维护规范。新增或修改文档时，先判断内容应该落在哪个唯一事实源，避免同一状态在多个文件重复维护。

## 文档分层

### 用户入口

- `../README.md`: 面向使用者，只放安装、快速开始、常用命令、核心架构和文档索引。
- `PROJECT_STATUS.md`: 当前项目状态唯一摘要，回答“现在做到哪、下一步做什么、主要限制是什么”。

### 项目执行

- `TASKS.md`: 任务状态唯一来源，使用 `- [ ]` 和 `- [x]` 维护 backlog、完成标准和验证命令。
- `WORKLOG.md`: 全量操作日志，记录关键决策、验证结果、阻塞点和完成记录。新记录必须追加到文件最底部，不删除历史记录。
- `ROADMAP.md`: 路线图唯一维护入口，只记录当前和未来方向。

### 稳定设计

- `PRD.md`: 产品定位、目标用户、核心价值和非目标。
- `TECH_STACK.md`: 技术栈、工程选型和主要依赖。
- `CONFIGURATION.md`: 配置项、环境变量、真实运行配置和默认值。
- `RETRIEVAL_DESIGN.md`: Retriever、搜索、抓取、chunk、去重和资料获取设计。

### 路线与验收

- `MVP_ACCEPTANCE.md`: MVP 验收指标、真实运行样例和复现命令。
- `REAL_BENCHMARK_GUIDE.md`: 真实 benchmark、local corpus smoke、指标解释和复现方式。
- `EVALUATION_LANGFUSE_PLAN.md`: Langfuse adapter、benchmark runner、LLM-as-Judge 和评测闭环设计。
- `archive/`: 历史 MVP 路线、Post-MVP 旧计划和早期实现计划。归档文档不再维护新任务状态。

### 示例

- `examples/`: 报告、评测 JSON 等示例产物。示例内容变化时，不代表核心规范变化。

## 唯一事实源

- 当前状态以 `PROJECT_STATUS.md` 为准。
- 路线规划以 `ROADMAP.md` 为准。
- 任务状态以 `TASKS.md` 为准。
- 操作历史以 `WORKLOG.md` 为准。
- 配置项以 `CONFIGURATION.md` 和 `.env.example` 为准。
- 评测复现方式以 `REAL_BENCHMARK_GUIDE.md` 为准。
- Langfuse 评测设计以 `EVALUATION_LANGFUSE_PLAN.md` 为准。

如果多个文档内容冲突，先更新唯一事实源，再在其他文档保留摘要或链接。

## 更新规则

- 改目录结构、配置项、CLI 命令、核心接口、schema、状态机、Retriever、Memory、Red-Blue 或 Evaluator 行为时，必须同步相关稳定设计文档。
- 超过一个文件或预计超过 30 分钟的任务，先在 `TASKS.md` 记录任务项。
- 每完成一个任务，立即把 `TASKS.md` 对应项标为完成，并在 `WORKLOG.md` 底部追加一条结果记录。
- `WORKLOG.md` 保存全量操作日志，不做“最近 N 条”裁剪；日志只写决策、验证结果、阻塞点和完成记录，不写临时思考。
- 过期但仍有追溯价值的设计不直接删除，优先移动到 `docs/archive/`，并在入口文件保留简短说明。
- 不要把同一段完整规划复制到多个文档；需要引用时使用链接和摘要。

## 推荐整理方向

后续可逐步收敛：

- 将 `MVP_ACCEPTANCE.md`、`REAL_BENCHMARK_GUIDE.md` 和 `EVALUATION_LANGFUSE_PLAN.md` 中重复的评测说明收敛到 `EVALUATION.md`。
- 将更多已完成且不再维护的历史设计移动到 `docs/archive/`。
