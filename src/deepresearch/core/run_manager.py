from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepresearch.agents.blue_agent import BlueAgent
from deepresearch.agents.evidence_quality import DefaultEvidenceQualityChecker
from deepresearch.agents.judge import Judge, JudgeConfig, RoundResult
from deepresearch.agents.planner import PlannerAgent
from deepresearch.agents.red_agent import RedAgent
from deepresearch.agents.researcher import ResearchAgent
from deepresearch.agents.synthesizer import Synthesizer
from deepresearch.config import DeepResearchConfig
from deepresearch.core.budget import (
    BudgetedEmbeddingClient,
    BudgetedLLMClient,
    BudgetedRerankerClient,
    BudgetedRetriever,
    RunBudget,
)
from deepresearch.core.dag import DAG
from deepresearch.core.executor import (
    DAGExecutor,
    ExecutorConfig,
    GlobalTimeoutError,
)
from deepresearch.core.trace import TraceEventType, TraceLogger
from deepresearch.embeddings.base import EmbeddingClient
from deepresearch.evaluation.langfuse import LangfuseAdapter
from deepresearch.evaluation.metrics import evaluate
from deepresearch.llm.base import LLMClient
from deepresearch.memory.milvus_store import export_snapshot
from deepresearch.memory.store import MemoryStore
from deepresearch.prompts.factory import build_prompt_provider
from deepresearch.prompts.provider import PromptProvider
from deepresearch.rerankers.base import RerankerClient
from deepresearch.retrieval.base import Retriever
from deepresearch.retrieval.fetcher import WebFetcher
from deepresearch.retrieval.lexical import LexicalPolicy, configure_lexical_policy
from deepresearch.schemas.evaluation import EvaluationResult
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState


@dataclass
class RunResult:
    run_id: str
    question: str
    report: ResearchReport
    evaluation: EvaluationResult
    plan_tasks: list[TaskNode]
    judge_rounds: list[RoundResult]
    output_dir: Path
    budget: RunBudget | None = None


class RunManager:
    def __init__(
        self,
        config: DeepResearchConfig,
        llm: LLMClient,
        retriever: Retriever,
        memory: MemoryStore,
        embedding: EmbeddingClient,
        reranker: RerankerClient,
        prompt_provider: PromptProvider | None = None,
    ) -> None:
        self._config = config
        self._llm = llm
        self._retriever = retriever
        self._memory = memory
        self._embedding = embedding
        self._reranker = reranker
        self._prompt_provider = prompt_provider
        self._langfuse: LangfuseAdapter | None = None
        self._configure_lexical_policy()

    async def run(
        self,
        question: str,
        *,
        output_dir: Path | None = None,
        langfuse_metadata: dict[str, Any] | None = None,
    ) -> RunResult:
        run_id = uuid.uuid4().hex[:12]
        out = output_dir or Path("outputs") / run_id
        out.mkdir(parents=True, exist_ok=True)

        trace = TraceLogger(out / "trace.jsonl", run_id=run_id)
        budget = RunBudget(max_llm_calls=self._config.executor.max_llm_calls_per_run)
        llm = BudgetedLLMClient(self._llm, budget)
        retriever = BudgetedRetriever(self._retriever, budget)
        embedding = BudgetedEmbeddingClient(self._embedding, budget)
        reranker = BudgetedRerankerClient(self._reranker, budget)
        deadline = time.monotonic() + self._config.executor.global_timeout_seconds

        prompt_provider = self._prompt_provider or self._build_prompt_provider()

        langfuse = LangfuseAdapter(
            enabled=self._config.langfuse.enabled,
            host=self._config.langfuse.host,
        )
        self._langfuse = langfuse
        langfuse_metadata = dict(langfuse_metadata or {})
        langfuse_metadata.setdefault("model_backend", self._config.llm.provider)
        langfuse_metadata.setdefault("prompt_label", self._config.langfuse.prompt_label)
        ctx = langfuse.context(
            run_id,
            question,
            {
                "experiment": self._config.langfuse.experiment_name,
                "llm": self._config.llm.model,
                "embedding": self._config.embedding.model,
                "retriever": self._config.retrieval.search_provider,
                "report_profile": self._config.synthesizer.report_profile,
                **langfuse_metadata,
            },
        )

        planner = PlannerAgent(llm, prompt_provider=prompt_provider)
        synthesizer = Synthesizer(
            llm,
            report_profile=self._config.synthesizer.report_profile,
            prompt_provider=prompt_provider,
        )
        red_agent = RedAgent(llm, prompt_provider=prompt_provider)
        blue_agent = BlueAgent(llm, prompt_provider=prompt_provider)
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
        with (
            ctx.create_phase("plan", {"question": question})
            if ctx
            else contextlib.nullcontext(None)
        ):
            plan = await planner.plan(question)
            trace.log(
                TraceEventType.PLANNER_CREATED_PLAN,
                {"plan_id": plan.plan_id, "task_count": len(plan.tasks)},
            )

        # Phase 2: Execute tasks
        dag = DAG(plan.tasks)
        execute_phase_id = ""

        async def task_fn(task: TaskNode) -> dict:
            def report_progress(stage: str, metadata: dict) -> None:
                if stage == "fetch_completed":
                    budget.fetched_docs += metadata.get("document_count", 0)
                elif stage == "chunking_completed":
                    budget.chunks += metadata.get("chunk_count", 0)
                trace.log(
                    TraceEventType.RETRIEVER_CALLED,
                    {"stage": stage, **metadata},
                    task_id=task.task_id,
                )

            researcher = self._build_research_agent(
                llm,
                retriever,
                embedding,
                reranker,
                progress=report_progress,
                prompt_provider=prompt_provider,
            )
            task_ctx_mgr = (
                ctx.create_task(task.task_id, task.description, execute_phase_id)
                if ctx and execute_phase_id
                else contextlib.nullcontext(None)
            )
            with task_ctx_mgr:
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

        executor_cfg = self._executor_config(deadline)

        with (
            ctx.create_phase("execute", {"task_count": len(plan.tasks)})
            if ctx
            else contextlib.nullcontext(None)
        ) as execute_phase:
            if ctx and execute_phase is not None:
                execute_phase_id = execute_phase.get("_observation_id", "")
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

        # Phase 2.5: Replan loop
        all_tasks = list(dag.tasks)
        for replan_round in range(self._config.executor.max_replans):
            request = executor.check_replan()
            if request is None:
                break
            trace.log(
                TraceEventType.REPLAN_REQUESTED,
                {
                    "round": replan_round + 1,
                    "trigger": request.trigger,
                    "reason": request.reason,
                    "affected_tasks": request.affected_tasks,
                    "actions": request.actions,
                },
            )
            replan_phase_ctx = (
                ctx.create_phase(
                    f"replan-{replan_round + 1}",
                    {"round": replan_round + 1, "trigger": request.trigger},
                )
                if ctx
                else contextlib.nullcontext(None)
            )
            with replan_phase_ctx:
                affected = [t for t in all_tasks if t.task_id in request.affected_tasks]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    replan_plan = await asyncio.wait_for(
                        planner.replan(
                            question,
                            request.trigger,
                            request.reason,
                            affected,
                            request.actions,
                        ),
                        timeout=remaining,
                    )
                except TimeoutError:
                    trace.log(
                        TraceEventType.TASK_STATE_CHANGED,
                        {
                            "status": "global_timeout",
                            "stage": "replan",
                            "round": replan_round + 1,
                        },
                    )
                    break
                replan_tasks, superseded = self._prepare_replan_tasks(
                    replan_plan.tasks,
                    all_tasks,
                    set(request.affected_tasks),
                    replan_round + 1,
                )
                for task in superseded:
                    task.status = TaskState.REPLANNING
                dag = DAG(replan_tasks)
                all_tasks.extend(replan_tasks)
                executor = DAGExecutor(
                    dag,
                    task_fn,
                    config=self._executor_config(deadline),
                    trace=trace,
                )
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
                trace.log(
                    TraceEventType.REPLAN_COMPLETED,
                    {
                        "round": replan_round + 1,
                        "new_task_count": len(replan_tasks),
                        "new_task_ids": [task.task_id for task in replan_tasks],
                        "superseded_task_ids": [task.task_id for task in superseded],
                    },
                )

        # Phase 3: Collect evidence from memory
        evidence_collector = self._collect_evidence(all_tasks)

        # Phase 4: Synthesize report
        with (
            ctx.create_phase(
                "synthesize",
                {"question": question, "evidence_count": len(evidence_collector)},
            )
            if ctx
            else contextlib.nullcontext(None)
        ):
            report = await synthesizer.synthesize(
                run_id, question, all_tasks, evidence_collector
            )
            trace.log(
                TraceEventType.LLM_CALLED,
                {"agent": "synthesizer", "section_count": len(report.sections)},
            )

        # Phase 5: Red-Blue review loop
        with (
            ctx.create_phase(
                "red-blue",
                {
                    "max_rounds": self._config.red_blue.max_rounds,
                    "target_score": self._config.red_blue.target_score,
                },
            )
            if ctx
            else contextlib.nullcontext(None)
        ):
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
        with ctx.create_phase("evaluate") if ctx else contextlib.nullcontext(None):
            eval_result = evaluate(
                run_id,
                all_tasks,
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
        budget.finish()
        trace.log(
            TraceEventType.EVALUATION_COMPLETED,
            {**eval_result.model_dump(mode="json"), "budget": budget.to_dict()},
        )

        report_payload = judge_result.report.model_dump(mode="json")
        evaluation_payload = eval_result.model_dump(mode="json")
        budget_payload = budget.to_dict()
        trace_summary = self._trace_summary(out / "trace.jsonl")
        if ctx is not None:
            ctx.end_run(
                evaluation_payload,
                budget_payload,
                report=report_payload,
                trace_summary=trace_summary,
            )
        else:
            langfuse.report_run(
                run_id,
                question,
                report_payload,
                evaluation_payload,
                budget_payload,
                {
                    "experiment": self._config.langfuse.experiment_name,
                    "llm": self._config.llm.model,
                    "embedding": self._config.embedding.model,
                    "retriever": self._config.retrieval.search_provider,
                    "report_profile": self._config.synthesizer.report_profile,
                },
                trace_summary,
                **langfuse_metadata,
            )

        # Write outputs
        await self._write_outputs(
            out,
            run_id,
            judge_result.report,
            eval_result,
            budget,
        )

        return RunResult(
            run_id=run_id,
            question=question,
            report=judge_result.report,
            evaluation=eval_result,
            plan_tasks=all_tasks,
            judge_rounds=judge_result.rounds,
            output_dir=out,
            budget=budget,
        )

    @staticmethod
    def _trace_summary(trace_path: Path) -> dict[str, Any]:
        if not trace_path.exists():
            return {"event_count": 0, "event_types": {}}
        counts: dict[str, int] = {}
        event_count = 0
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_count += 1
            event_type = event.get("event_type", "unknown")
            counts[event_type] = counts.get(event_type, 0) + 1
        return {"event_count": event_count, "event_types": counts}

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
        budget: RunBudget,
    ) -> None:
        (out / "report.md").write_text(self._format_report_md(report), encoding="utf-8")
        (out / "evaluation.json").write_text(
            json.dumps(
                {
                    **evaluation.model_dump(mode="json"),
                    "budget": budget.to_dict(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        await export_snapshot(
            self._memory,
            run_id,
            out / "memory_snapshot.jsonl",
        )

    def _executor_config(self, deadline: float) -> ExecutorConfig:
        remaining = max(0.0, deadline - time.monotonic())
        return ExecutorConfig(
            max_concurrency=self._config.executor.max_concurrency,
            max_task_retries=self._config.executor.max_task_retries,
            task_timeout_seconds=self._config.executor.task_timeout_seconds,
            global_timeout_seconds=remaining,
            max_llm_calls_per_run=self._config.executor.max_llm_calls_per_run,
        )

    def _build_research_agent(
        self,
        llm: LLMClient,
        retriever: Retriever,
        embedding: EmbeddingClient,
        reranker: RerankerClient,
        *,
        progress: Any,
        prompt_provider: PromptProvider | None,
    ) -> ResearchAgent:
        return ResearchAgent(
            llm,
            retriever,
            self._memory,
            embedding,
            reranker,
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
            progress=progress,
            prompt_provider=prompt_provider,
        )

    def _build_prompt_provider(self) -> PromptProvider | None:
        return build_prompt_provider(self._config.langfuse)

    def _configure_lexical_policy(self) -> None:
        configure_lexical_policy(
            LexicalPolicy(
                tokenizer=self._config.lexical.tokenizer,
                latin_min_chars=self._config.lexical.latin_min_chars,
                cjk_ngrams=tuple(self._config.lexical.cjk_ngrams),
                cjk_ngram_fallback=self._config.lexical.cjk_ngram_fallback,
                userdict_path=self._config.lexical.userdict_path,
            )
        )

    @staticmethod
    def _prepare_replan_tasks(
        replacements: list[TaskNode],
        all_tasks: list[TaskNode],
        affected_ids: set[str],
        round_num: int,
    ) -> tuple[list[TaskNode], list[TaskNode]]:
        existing_ids = {task.task_id for task in all_tasks}

        def unique_id(base: str) -> str:
            candidate = base
            suffix = 2
            while candidate in existing_ids:
                candidate = f"{base}-{suffix}"
                suffix += 1
            existing_ids.add(candidate)
            return candidate

        replacement_id_map = {
            task.task_id: unique_id(f"replan-{round_num}-{task.task_id}")
            for task in replacements
        }
        prepared_replacements = [
            task.model_copy(
                update={
                    "task_id": replacement_id_map[task.task_id],
                    "dependencies": [
                        replacement_id_map[dependency]
                        for dependency in task.dependencies
                        if dependency in replacement_id_map
                    ],
                    "status": TaskState.PENDING,
                    "retries": 0,
                    "error": None,
                    "result": None,
                    "input": {
                        **task.input,
                        "replan_round": round_num,
                        "replaces": sorted(affected_ids),
                    },
                }
            )
            for task in replacements
        ]
        depended_on = {
            dependency
            for task in prepared_replacements
            for dependency in task.dependencies
        }
        replacement_terminals = [
            task.task_id
            for task in prepared_replacements
            if task.task_id not in depended_on
        ]

        resumable: list[TaskNode] = []
        resumable_ids: set[str] = set()
        changed = True
        while changed:
            changed = False
            for task in all_tasks:
                if task.status not in {TaskState.SKIPPED, TaskState.CANCELLED}:
                    continue
                if task.task_id in resumable_ids:
                    continue
                if any(
                    dependency in affected_ids or dependency in resumable_ids
                    for dependency in task.dependencies
                ):
                    resumable.append(task)
                    resumable_ids.add(task.task_id)
                    changed = True

        resume_id_map = {
            task.task_id: unique_id(f"replan-{round_num}-resume-{task.task_id}")
            for task in resumable
        }
        resumed_tasks = []
        for task in resumable:
            dependencies: list[str] = []
            for dependency in task.dependencies:
                if dependency in affected_ids:
                    dependencies.extend(replacement_terminals)
                elif dependency in resume_id_map:
                    dependencies.append(resume_id_map[dependency])
            resumed_tasks.append(
                task.model_copy(
                    update={
                        "task_id": resume_id_map[task.task_id],
                        "dependencies": list(dict.fromkeys(dependencies)),
                        "status": TaskState.PENDING,
                        "retries": 0,
                        "error": None,
                        "result": None,
                        "input": {
                            **task.input,
                            "replan_round": round_num,
                            "resumes": task.task_id,
                        },
                    }
                )
            )

        superseded = [
            task
            for task in all_tasks
            if task.task_id in affected_ids or task.task_id in resumable_ids
        ]
        return prepared_replacements + resumed_tasks, superseded

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
