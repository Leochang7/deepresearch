# DeepResearch Agent

面向复杂深度研究任务的多智能体协作系统。项目目标是构建一个可执行、可追踪、可评测的深度研究报告生成系统，覆盖任务规划、DAG 并发执行、共享记忆、Red-Blue 对抗修复和结果评测。

## 文档

- [PRD：产品需求文档](docs/PRD.md)
- [MVP 范围与后续路线](docs/MVP_AND_ROADMAP.md)
- [项目实现规划](docs/IMPLEMENTATION_PLAN.md)
- [技术栈与工程选型](docs/TECH_STACK.md)
- [检索与资料获取设计](docs/RETRIEVAL_DESIGN.md)
- [配置设计](docs/CONFIGURATION.md)

## 当前定位

本项目不是普通聊天式 Research Agent，而是一个强调工程闭环的研究系统：

- Planner 将复杂问题拆解为可执行 DAG。
- Executor 基于 `asyncio` 与信号量控制并发、超时和降级。
- Retriever 通过统一接口接入本地资料集、搜索 API、浏览器抓取、MCP 工具和模型原生搜索。
- Memory 基于 Milvus 保存跨 Agent 证据、摘要、向量和冲突信息。
- Synthesizer 生成带引用的结构化研究报告。
- Red Agent 审查事实性、逻辑一致性和引用质量。
- Blue Agent 根据审查结果修复报告。
- Evaluator 输出可复现实验指标和执行 trace。
