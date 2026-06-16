# Post-MVP Roadmap

MVP 已证明核心链路可运行：Planner -> DAG Executor -> Research Agent -> Retriever -> Memory -> Synthesizer -> Red/Blue/Judge -> Evaluator。MVP 之后的目标不是继续堆 Agent 名称，而是把真实运行变得稳定、可诊断、可展示、可评测。

## 1. 执行优先级

### P0：真实环境自检与工程可靠性

优先做 `deepresearch doctor`，原因是真实验收已经暴露出三类配置风险：

- embedding endpoint 实际维度可能与文档假设不同。
- reranker 模型名可能不存在。
- Milvus collection schema 可能和 embedding 维度不匹配。

`doctor` 应检查：

- 必需环境变量是否存在，但不打印密钥值。
- MiMo、Tavily、embedding、reranker endpoint 是否可访问。
- embedding `/models` 中模型维度是否和 `DEEPRESEARCH_EMBEDDING_DIM` 一致。
- reranker `/models` 中是否存在配置模型。
- Milvus Standalone 是否可连接。
- collection 是否存在、向量维度是否和当前 embedding 配置一致。
- Docker Milvus 是否启动，必要时提示 `docker compose -f docker-compose.milvus.yml up -d`。

同时增加真实模式测试入口：

- `uv run pytest -m integration`
- `uv run pytest -m e2e`
- `uv run pytest -m network`
- `uv run pytest -m milvus`
- `uv run pytest -m llm`

默认 `uv run pytest` 继续保持离线、无 API key、无 Milvus 服务可跑。

### P1：检索质量增强

第一项做 RRF，而不是先做复杂重排策略。

RRF 适合当前项目，因为 Tavily、MiMo Search、LocalDataset、Milvus recall 的分数尺度不同，直接比较 raw score 不可靠。RRF 只依赖 rank，适合多 query、多 retriever、多候选列表融合。

第一版只做标准 RRF：

```text
score(d) = sum(1 / (rrf_k + rank_i(d)))
```

默认参数：

- `rrf_k = 60`
- `max_fused_results = 20`

先做 document-level RRF：

```text
multi-query search results -> RRF -> fetch top docs -> chunk
```

后续再做 chunk-level RRF：

```text
Milvus vector recall + keyword/BM25 recall + source-priority chunks -> RRF -> reranker
```

RRF 之后补 MMR（Maximal Marginal Relevance）。两者职责不同：

- RRF：融合多个检索器或多个 query 的 ranked list。
- MMR：在融合后的候选池中做多样性选择，减少同源、同义、重复片段挤占上下文。

MMR 第一版放在 chunk selection 阶段：

```text
RRF fused chunks -> reranker score -> MMR diversity selection -> context pack
```

默认参数：

- `mmr_lambda = 0.7`
- `max_context_chunks = 12`
- 相似度使用 chunk embedding cosine similarity。

去重 key：

- document 阶段：`canonical_url` 优先，其次 `title + content_hash`
- chunk 阶段：`source_url + content_hash`

暂不做动态权重，后续可扩展 weighted RRF：

```text
weighted_score(d) = sum(weight_i / (rrf_k + rank_i(d)))
```

### P2：引用与证据质量

当前报告已经能输出 URL，但引用质量还需要继续增强：

- References 去重。
- References 输出 `title + url + retrieved_at`。
- 正文关键事实至少绑定一个 evidence id。
- Red Agent 专门验证“引用是否真的支持该句”。
- Evidence quote 必须原文命中。
- Claim 与 quote 做语义一致性校验。
- 低置信 evidence 不进入最终 synthesis。
- Evidence 按 task、section、source 分组。

报告模板也要变得更可控。建议支持 report profile：

- `factual_answer`
- `comparison`
- `timeline`
- `tech_research`
- `risk_analysis`

### P3：Agent 编排与 replan 闭环

当前 executor 有 replan 触发和降级雏形，但真实 run 还没有做到“失败后生成替代 task 并继续执行”。这是项目核心卖点，需要补强。

目标：

- 单任务失败后生成 alternate queries。
- evidence 为 0 时追加替代研究任务。
- 同层失败率过高时 replan 当前 DAG layer。
- replan 产生的新 task 要进入同一个 trace。
- 最终报告中清楚区分 completed、replanned、skipped、failed task。

同时补 run budget：

- LLM calls。
- search calls。
- fetched docs。
- chunks。
- embedding batches。
- rerank calls。
- token usage。
- elapsed time。

### P4：Trace、Inspect 与展示

优先增强 CLI，而不是马上做 Web UI。

建议增加：

```bash
uv run deepresearch inspect <run_id> --timeline
uv run deepresearch inspect <run_id> --tasks
uv run deepresearch inspect <run_id> --evidence
```

输出应包括：

- 每个 task 的耗时。
- 每个 task 卡在哪个阶段。
- 每个 task 的 query/doc/chunk/evidence 数量。
- 失败原因。
- Red-Blue 每轮 score、issues、actions。

后续再做：

- README demo 截图。
- 示例问题集 `examples/questions.txt`。
- `docs/MVP_ACCEPTANCE.md` 固化真实验收结果。
- Web UI 或 dashboard。

### P5：Memory 与数据治理

Memory 需要避免“collection 维度/模型混用”再次发生。

优先做：

- Memory schema version。
- collection metadata 记录 embedding model、dim、created_at。
- 启动时校验当前配置与 collection metadata。
- 跨 run source cache。
- evidence reuse。
- stale source 检测。

冲突检测第一版不要上复杂 NLI，先做轻量规则：

- 同实体不同日期。
- 同实体不同数值。
- 高相似 claim 但结论词相反。
- 同 source_url 不同 claim。

### P6：Langfuse 评测闭环

最后补 benchmark，但不在本项目内自研完整评测平台。PM6 改为 Langfuse 驱动的评测闭环：Langfuse 负责 trace、dataset、experiment run、score 记录和对比展示；本项目保留 dataset、runner、规则指标、LLM-as-Judge schema 和可复现实验入口。

顺序：

1. 接入可选 Langfuse adapter，不影响默认离线测试。
2. 固化 ResearchBench mini，先做 10-15 个可复现 case。
3. 实现 `deepresearch benchmark` runner，输出 JSONL 和 summary。
4. 本地扩展 `factual_hit_rate` 与 `hallucination_flag`。
5. 增加 LLM-as-Judge 五维评分，并可写入 Langfuse scores。
6. pipeline 稳定后，再扩到 ResearchBench 11 领域/35 题、HotpotQA 深度研究变体、Bootstrap 95% CI、Cohen's d 和多后端实验脚本。

详细设计见 [Langfuse Evaluation Plan](EVALUATION_LANGFUSE_PLAN.md)。

### P7：真实 benchmark 质量校准

PM6 已经让 benchmark runner、Langfuse adapter、规则指标、LLM-as-Judge 和统计摘要可运行。下一步不是继续增加新 Agent 或 Web UI，而是校准真实 benchmark 的质量判断，让指标能解释真实报告。

当前真实 `rb-002` 复测显示执行链路已经恢复：

- `task_success_rate = 1.0`
- `citation_coverage = 0.7143`
- `empty_citation_rate = 0.0`
- `hallucination_flag = false`

但 `factual_hit_rate = 0.0`，原因是当前指标主要依赖 expected fact 与报告正文的字符串/token overlap。真实报告经常会用不同表述覆盖同一事实，导致“语义上覆盖、规则上 miss”。因此 PM7 的目标是把事实覆盖率从粗糙字符串命中升级为 fact-level 可解释评测。

PM7 范围：

- 将每条 `expected_facts` 拆成独立 fact item。
- 本地规则支持关键词组、别名、归一化和命中原因。
- 增加 fact-level semantic judge，输出 `hit/miss/uncertain`。
- 每条 fact 记录 supporting evidence ids 和 miss reason。
- `results.jsonl` 输出 per-fact 明细。
- `summary.json` 聚合 per-case failure reason、domain/difficulty breakdown 和事实覆盖分布。
- 真实 smoke 先跑 5 个 case，再考虑跑完整 mini dataset。

PM7 不做：

- 不扩充到大规模 35 题 benchmark。
- 不做 Web dashboard。
- 不把 Langfuse 作为必需依赖。
- 不为了提高分数放宽 citation/hallucination 规则。

验收标准：

- 默认 `uv run pytest` 仍然离线通过。
- `uv run deepresearch doctor --real` 全绿。
- 真实 5-case benchmark 能解释每个 case 的主要失败原因。
- `factual_hit_rate` 不再因为同义改写系统性归零。
- Langfuse 可选开启时能记录 fact-level scores。

### P8：Local Corpus 可复现真实评测

PM7 暴露出一个更基础的问题：实时联网搜索不适合作为早期 benchmark 主路径。MiMo 原生联网搜索按量计费，Tavily 免费额度有限且会返回 432；即使搜索成功，结果也受时间、额度、网络和排序波动影响，不利于调试 evidence extraction、citation coverage 和 Red-Blue。

因此下一步改成 Local Corpus 优先：

```text
ResearchBench smoke question -> LocalDatasetRetriever -> fetch/chunk/embed -> Milvus -> Synthesizer -> Red-Blue -> Evaluator
```

原则：

- benchmark 默认不依赖 Tavily/MiMo Search。
- 本地 corpus 是可提交、可复现、可审查的资料集。
- 真实模式仍使用真实 MiMo chat、Qwen embedding、bge reranker 和 Milvus Standalone。
- 联网搜索作为 optional retriever adapter，只用于探索和增强，不作为稳定验收依赖。
- 先验证“给到资料后系统能否抽证据、写引用、降低幻觉”，再评估实时搜索质量。

PM8 范围：

- 为 PM7 5-case smoke 准备本地 corpus。
- `benchmark` CLI 支持 `--retriever local --corpus examples/corpus`。
- 准备低成本 smoke 配置，限制 query/docs/chunks/replan/Red-Blue 轮数。
- 跑通 local-corpus real benchmark。
- 基于可控资料集修复 evidence extraction 和 citation coverage。
- 将 Tavily/MiMo Search 文档定位调整为 optional network adapter。

PM8 不做：

- 不继续消耗 MiMo/Tavily 实时搜索额度跑 benchmark。
- 不把免费搜索 API 当作稳定基础设施。
- 不为了指标好看引入不真实的引用。
- 不扩大到 35 题，直到 5-case local smoke 稳定。

## 2. 推荐下一步

下一步优先做 PM8：Local Corpus 可复现真实评测。

原因是 PM7 已完成 fact-level 评测能力，但实时联网搜索已经成为成本和复现性的瓶颈。先用本地 corpus 固化资料输入，才能判断 ResearchAgent、evidence extraction、citation coverage、Red-Blue 和 evaluator 是否真的可靠。等 local-corpus smoke 稳定后，再把 Tavily/MiMo/SearXNG/Brave 等网络检索作为增强层接回去。
