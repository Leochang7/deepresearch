# Future Ideas

本文件保存暂未实现、暂不作为当前路线承诺维护的扩展想法。主文档只描述已实现能力和当前验收路径；如果这些想法重新进入执行范围，再移动到 `ROADMAP.md` 和 `TASKS.md`。

## Retrieval

- `BrowserRetriever`: 使用浏览器自动化抓取动态网页、登录后页面或反爬较强页面，并统一输出 `RetrievedDocument`。
- `MCPRetriever`: 通过 MCP 接入 GitHub、论文库、数据库、文件系统或内部知识库。
- `ModelNativeSearchRetriever`: 抽象不同模型厂商的原生搜索能力，作为 demo 或 baseline，而不是核心检索唯一来源。
- 其他搜索 API: SerpAPI、Bing Search API、Brave Search API。

## Storage And Ops

- Milvus Distributed 或托管 Milvus。
- PostgreSQL 结构化分析库。
- Prometheus/Grafana 运行监控。
- Qdrant、pgvector 或 FAISS 作为非主线向量后端对比。

## Product Surface

- Web Demo。
- DAG 可视化。
- 报告 diff 和 Red-Blue 过程展示。
