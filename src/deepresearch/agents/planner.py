from __future__ import annotations

import uuid
from pathlib import Path

from deepresearch.core.dag import DAG, CycleError
from deepresearch.core.json_repair import parse_json
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.schemas.task import ResearchPlan, TaskNode

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner.md"


class PlannerAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._system_prompt = (
            _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""
        )

    async def plan(self, question: str) -> ResearchPlan:
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(role="user", content=f"Research question: {question}"),
        ]

        response = await self._llm.chat(messages, json_mode=True)
        data = parse_json(response.content, strict=False)

        try:
            return self._build_validated_plan(question, data)
        except (TypeError, ValueError, CycleError):
            return self._fallback_plan(question)

    async def replan(
        self,
        question: str,
        trigger: str,
        reason: str,
        affected_tasks: list[TaskNode],
        actions: list[str],
    ) -> ResearchPlan:
        task_summaries = "\n".join(
            f"- [{t.task_id}] {t.description} (status={t.status.value})"
            + (f" error={t.error}" if t.error else "")
            + (
                f" info_insufficient={t.result.get('information_insufficient')}"
                if t.result and t.result.get("information_insufficient")
                else ""
            )
            for t in affected_tasks
        )
        actions_text = ", ".join(actions)
        user_msg = (
            f"Research question: {question}\n\n"
            f"Replan trigger: {trigger}\n"
            f"Reason: {reason}\n"
            f"Suggested actions: {actions_text}\n\n"
            f"Affected tasks:\n{task_summaries}\n\n"
            "Generate alternative tasks to address these failures. "
            "Use different search queries or approaches. "
            "Return a JSON object with a 'tasks' array."
        )
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(role="user", content=user_msg),
        ]
        response = await self._llm.chat(messages, json_mode=True)
        data = parse_json(response.content, strict=False)

        try:
            return self._build_validated_plan(question, data)
        except (TypeError, ValueError, CycleError):
            return self._replan_fallback(question, affected_tasks)

    def _build_validated_plan(self, question: str, data: dict | None) -> ResearchPlan:
        if not isinstance(data, dict):
            raise TypeError("Planner response must be a JSON object")
        raw_tasks = data.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ValueError("Planner response must contain tasks")

        tasks: list[TaskNode] = []
        for index, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, dict):
                raise TypeError("Each task must be a JSON object")
            tasks.append(
                TaskNode(
                    task_id=str(raw_task.get("task_id") or f"t{index + 1}"),
                    description=str(raw_task.get("description", "")).strip(),
                    goal=str(raw_task.get("goal", "")).strip(),
                    dependencies=list(raw_task.get("dependencies") or []),
                    priority=int(raw_task.get("priority", 0)),
                )
            )

        task_ids = [task.task_id for task in tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Planner response contains duplicate task IDs")
        if any(not task.description for task in tasks):
            raise ValueError("Planner response contains an empty task description")

        DAG(tasks).validate()
        return ResearchPlan(
            plan_id=str(data.get("plan_id") or uuid.uuid4()),
            question=question,
            tasks=tasks,
        )

    @staticmethod
    def _fallback_plan(question: str) -> ResearchPlan:
        return ResearchPlan(
            plan_id=str(uuid.uuid4()),
            question=question,
            tasks=[
                TaskNode(
                    task_id="t1",
                    description=question,
                    goal="Research the topic",
                    dependencies=[],
                    priority=1,
                )
            ],
        )

    @staticmethod
    def _replan_fallback(question: str, affected_tasks: list[TaskNode]) -> ResearchPlan:
        tasks = [
            TaskNode(
                task_id=f"replan-{t.task_id}",
                description=f"Retry: {t.description}",
                goal=t.goal or "Retry with alternative approach",
                dependencies=[],
                priority=t.priority + 1,
            )
            for t in affected_tasks
        ]
        return ResearchPlan(
            plan_id=str(uuid.uuid4()),
            question=question,
            tasks=tasks,
        )
