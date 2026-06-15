from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from deepresearch.agents.blue_agent import BlueAgent
from deepresearch.agents.evidence_quality import DefaultEvidenceQualityChecker
from deepresearch.agents.judge import Judge, JudgeConfig, RoundResult
from deepresearch.agents.planner import PlannerAgent
from deepresearch.agents.red_agent import RedAgent
from deepresearch.agents.researcher import ResearchAgent
from deepresearch.agents.synthesizer import Synthesizer
from deepresearch.config import DeepResearchConfig
from deepresearch.core.dag import DAG
from deepresearch.core.executor import DAGExecutor, ExecutorConfig, GlobalTimeoutError
from deepresearch.core.trace import TraceEventType, TraceLogger
from deepresearch.embeddings.base import EmbeddingClient
from deepresearch.evaluation.metrics import evaluate
from deepresearch.llm.base import LLMClient
from deepresearch.memory.milvus_store import export_snapshot
from deepresearch.memory.store import MemoryStore
from deepresearch.rerankers.base import RerankerClient
from deepresearch.retrieval.base import Retriever
from deepresearch.retrieval.fetcher import WebFetcher
from deepresearch.schemas.evaluation import EvaluationResult
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport
from deepresearch.schemas.task import TaskNode


@dataclass
class RunResult:
    run_id: str
    question: str
    report: ResearchReport
    evaluation: EvaluationResult
    plan_tasks: list[TaskNode]
    judge_rounds: list[RoundResult]
    output_dir: Path


class RunManager:
    def __init__(
        self,
        config: DeepResearchConfig,
        llm: LLMClient,
        retriever: Retriever,
        memory: MemoryStore,
        embedding: EmbeddingClient,
        reranker: RerankerClient,
    ) -> None:
        self._config = config
        self._llm = llm
        self._retriever = retriever
        self._memory = memory
        self._embedding = embedding
        self._reranker = reranker

    async def run(
        self,
        question: str,
        *,
        output_dir: Path | None = None,
    ) -> RunResult:
        run_id = uuid.uuid4().hex[:12]
        out = output_dir or Path("outputs") / run_id
        out.mkdir(parents=True, exist_ok=True)

        trace = TraceLogger(out / "trace.jsonl", run_id=run_id)

        planner = PlannerAgent(self._llm)
        synthesizer = Synthesizer(
            self._llm, report_profile=self._config.synthesizer.report_profile
        )
        red_agent = RedAgent(self._llm)
        blue_agent = BlueAgent(self._llm)
        judge = Judge(
            JudgeConfig(
                max_rounds=self._config.red_blue.max_rounds,
                target_score=self._config.red_blue.target_score,
                min_score_delta=self._config.red_blue.min_score_delta,
                oscillation_window=self._config.red_blue.oscillation_window,
            ),
            red_agent=red_agent,
            blue_agent=blue_agent,
        )

        # Phase 1: Plan
        plan = await planner.plan(question)
        trace.log(
            TraceEventType.PLANNER_CREATED_PLAN,
            {"plan_id": plan.plan_id, "task_count": len(plan.tasks)},
        )

        # Phase 2: Execute tasks
        dag = DAG(plan.tasks)

        async def task_fn(task: TaskNode) -> dict:
            def report_progress(stage: str, metadata: dict) -> None:
                trace.log(
                    TraceEventType.RETRIEVER_CALLED,
                    {"stage": stage, **metadata},
                    task_id=task.task_id,
                )

            researcher = ResearchAgent(
                self._llm,
                self._retriever,
                self._memory,
                self._embedding,
                self._reranker,
                fetcher=WebFetcher(
                    timeout=self._config.fetch.timeout_seconds,
                    max_retries=self._config.fetch.max_retries,
                    user_agent=self._config.fetch.user_agent,
                ),
                quality_checker=DefaultEvidenceQualityChecker(
                    min_confidence=self._config.evidence_quality.min_confidence,
                    min_token_overlap=self._config.evidence_quality.min_token_overlap,
                ),
                max_queries=self._config.retrieval.max_queries_per_task,
                max_documents=self._config.retrieval.max_docs_per_task,
                max_chunks=self._config.retrieval.max_chunks_per_task,
                vector_top_k=self._config.retrieval.top_k_vector,
                rerank_top_k=self._config.retrieval.top_k_reranked,
                rrf_k=self._config.fusion.rrf_k,
                max_fused_docs=self._config.fusion.max_fused_docs,
                max_fused_chunks=self._config.fusion.max_fused_chunks,
                mmr_lambda=self._config.fusion.mmr_lambda,
                max_mmr_results=self._config.fusion.max_mmr_results,
                fetch_concurrency=min(
                    self._config.retrieval.max_docs_per_task,
                    10,
                ),
                progress=report_progress,
            )
            trace.log(
                TraceEventType.RETRIEVER_CALLED,
                {"stage": "research_started"},
                task_id=task.task_id,
            )
            result = await researcher.execute(task, run_id=run_id)
            trace.log(
                TraceEventType.MILVUS_UPSERTED,
                {
                    "chunk_count": result.get("chunk_count", 0),
                    "evidence_count": result.get("evidence_count", 0),
                },
                task_id=task.task_id,
            )
            return result

        executor_cfg = ExecutorConfig(
            max_concurrency=self._config.executor.max_concurrency,
            max_task_retries=self._config.executor.max_task_retries,
            task_timeout_seconds=self._config.executor.task_timeout_seconds,
            global_timeout_seconds=self._config.executor.global_timeout_seconds,
        )
        executor = DAGExecutor(dag, task_fn, config=executor_cfg, trace=trace)
        try:
            await executor.run()
        except GlobalTimeoutError as error:
            trace.log(
                TraceEventType.TASK_STATE_CHANGED,
                {
                    "status": "global_timeout",
                    "partial_result": error.partial_result,
                },
            )

        # Phase 3: Collect evidence from memory
        evidence_collector = self._collect_evidence(dag.tasks)

        # Phase 4: Synthesize report
        report = await synthesizer.synthesize(
            run_id, question, plan.tasks, evidence_collector
        )
        trace.log(
            TraceEventType.LLM_CALLED,
            {"agent": "synthesizer", "section_count": len(report.sections)},
        )

        # Phase 5: Red-Blue review loop
        judge_result = await judge.run(report, evidence_collector)
        for round_result in judge_result.rounds:
            trace.log(
                TraceEventType.RED_REVIEW_CREATED,
                {
                    "round": round_result.round_num,
                    "score": round_result.post_fix_score,
                    "issues": round_result.issues_count,
                },
            )
            trace.log(
                TraceEventType.BLUE_FIX_APPLIED,
                {
                    "round": round_result.round_num,
                    "actions": round_result.actions_count,
                    "rejected_actions": round_result.rejected_actions,
                },
            )

        # Phase 6: Evaluate
        eval_result = evaluate(
            run_id,
            plan.tasks,
            judge_result.report,
            evidence_collector,
            red_issues=[
                {"round": result.round_num, "index": index}
                for result in judge_result.rounds
                for index in range(result.issues_count)
            ],
            blue_actions=[
                {"round": result.round_num, "index": index}
                for result in judge_result.rounds
                for index in range(result.actions_count)
            ],
        )
        eval_result.judge_scores = {
            "final_score": judge_result.final_score,
            "rounds": float(len(judge_result.rounds)),
        }
        trace.log(
            TraceEventType.EVALUATION_COMPLETED,
            eval_result.model_dump(mode="json"),
        )

        # Write outputs
        await self._write_outputs(
            out,
            run_id,
            judge_result.report,
            eval_result,
        )

        return RunResult(
            run_id=run_id,
            question=question,
            report=judge_result.report,
            evaluation=eval_result,
            plan_tasks=plan.tasks,
            judge_rounds=judge_result.rounds,
            output_dir=out,
        )

    @staticmethod
    def _collect_evidence(tasks: list[TaskNode]) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        evidence_index = 1
        seen: set[tuple[str, str, str | None]] = set()
        for task in tasks:
            if not task.result:
                continue
            for raw in task.result.get("evidence", []):
                item = EvidenceItem.model_validate(raw)
                key = (item.claim, item.quote, item.source_url)
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(
                    item.model_copy(update={"evidence_id": f"E{evidence_index}"})
                )
                evidence_index += 1
        return evidence

    async def _write_outputs(
        self,
        out: Path,
        run_id: str,
        report: ResearchReport,
        evaluation: EvaluationResult,
    ) -> None:
        (out / "report.md").write_text(self._format_report_md(report), encoding="utf-8")
        (out / "evaluation.json").write_text(
            evaluation.model_dump_json(indent=2), encoding="utf-8"
        )
        await export_snapshot(
            self._memory,
            run_id,
            out / "memory_snapshot.jsonl",
        )

    @staticmethod
    def _format_report_md(report: ResearchReport) -> str:
        parts = [f"# {report.question}"]
        if report.summary:
            parts.append(f"\n## Executive Summary\n{report.summary}")
        for section in report.sections:
            if section.title.strip().lower() in {"executive summary", "summary"}:
                continue
            parts.append(f"\n## {section.title}\n{section.content}")
        if report.limitations:
            parts.append("\n## Limitations")
            for lim in report.limitations:
                parts.append(f"- {lim}")
        if report.references:
            parts.append("\n## References")
            for ref in report.references:
                parts.append(f"- {ref}")
        return "\n".join(parts)
