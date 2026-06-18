from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from deepresearch.core.dag import DAG
from deepresearch.core.trace import TraceEventType, TraceLogger
from deepresearch.schemas.task import TaskNode, TaskState


@dataclass
class ExecutorConfig:
    max_concurrency: int = 1
    max_task_retries: int = 2
    task_timeout_seconds: float = 180.0
    global_timeout_seconds: float = 1800.0
    max_llm_calls_per_run: int = 80


TaskFn = Callable[[TaskNode], Awaitable[dict[str, Any]]]


class TaskFailedError(Exception):
    def __init__(self, task_id: str, cause: Exception) -> None:
        self.task_id = task_id
        self.cause = cause
        super().__init__(f"Task {task_id} failed: {cause}")


class GlobalTimeoutError(Exception):
    def __init__(self, message: str, partial_result: dict[str, Any]) -> None:
        self.partial_result = partial_result
        super().__init__(message)


class ReplanRequest(Exception):
    def __init__(
        self,
        reason: str,
        failed_tasks: list[str] | None = None,
        *,
        trigger: str = "task_failure",
        level: str = "task",
        affected_tasks: list[str] | None = None,
        actions: list[str] | None = None,
        limitations: list[str] | None = None,
    ) -> None:
        self.reason = reason
        self.failed_tasks = failed_tasks or []
        self.trigger = trigger
        self.level = level
        self.affected_tasks = affected_tasks or self.failed_tasks.copy()
        self.actions = actions or []
        self.limitations = limitations or []
        super().__init__(f"Replan requested: {reason}")


class DAGExecutor:
    def __init__(
        self,
        dag: DAG,
        task_fn: TaskFn,
        *,
        config: ExecutorConfig | None = None,
        trace: TraceLogger | None = None,
        on_task_complete: Callable[[TaskNode], Awaitable[None]] | None = None,
    ) -> None:
        self._dag = dag
        self._task_fn = task_fn
        self._config = config or ExecutorConfig()
        self._trace = trace
        self._on_complete = on_task_complete
        self._semaphore = asyncio.Semaphore(self._config.max_concurrency)
        self._start_time: float = 0
        self._cancelled = False
        self._completed_tasks: set[str] = set()
        self._failed_tasks: list[str] = []
        self._failure_attempts: dict[str, int] = {}

    async def run(self) -> dict[str, Any]:
        self._start_time = time.monotonic()
        self._dag.validate()

        try:
            await asyncio.wait_for(
                self._run_loop(),
                timeout=self._config.global_timeout_seconds,
            )
        except TimeoutError:
            self._cancel_remaining()
            partial_result = self._build_result()
            partial_result.update(
                {
                    "degradation_level": "global_timeout",
                    "force_synthesis": True,
                    "limitations": self._build_timeout_limitations(),
                }
            )
            raise GlobalTimeoutError(
                f"Global timeout ({self._config.global_timeout_seconds}s) exceeded",
                partial_result,
            ) from None

        return self._build_result()

    async def _run_loop(self) -> None:
        while True:
            if self._cancelled:
                break

            self._skip_blocked_tasks()

            ready = self._dag.ready_tasks()
            if not ready:
                if self._all_terminal():
                    break
                await asyncio.sleep(0.01)
                continue

            tasks_to_run = [t for t in ready if t.task_id not in self._completed_tasks]
            if not tasks_to_run:
                await asyncio.sleep(0.01)
                continue

            coros = [self._execute_task(task) for task in tasks_to_run]
            await asyncio.gather(*coros)

    def _all_terminal(self) -> bool:
        terminal_states = {
            TaskState.SUCCEEDED,
            TaskState.FAILED,
            TaskState.SKIPPED,
            TaskState.CANCELLED,
            TaskState.REPLANNING,
        }
        return all(t.status in terminal_states for t in self._dag.tasks)

    def _skip_blocked_tasks(self) -> None:
        for task in self._dag.tasks:
            if task.status != TaskState.PENDING:
                continue
            deps = self._dag.dependencies(task.task_id)
            if not deps:
                continue
            if any(
                self._dag.get(dep_id).status
                in (TaskState.FAILED, TaskState.CANCELLED, TaskState.SKIPPED)
                for dep_id in deps
            ):
                self._set_status(
                    task,
                    TaskState.SKIPPED,
                    {"status": "skipped", "reason": "dependency_failed"},
                )

    async def _execute_task(self, task: TaskNode) -> None:
        async with self._semaphore:
            if self._cancelled:
                return

            if task.status != TaskState.PENDING:
                return

            self._set_status(task, TaskState.READY, trace=False)
            self._set_status(task, TaskState.RUNNING, {"status": "running"})

            for attempt in range(self._config.max_task_retries + 1):
                try:
                    result = await asyncio.wait_for(
                        self._task_fn(task),
                        timeout=self._config.task_timeout_seconds,
                    )
                    task.result = result
                    self._completed_tasks.add(task.task_id)
                    self._set_status(
                        task,
                        TaskState.SUCCEEDED,
                        {"status": "succeeded"},
                    )
                    if self._on_complete:
                        await self._on_complete(task)
                    return
                except TimeoutError:
                    self._failure_attempts[task.task_id] = attempt + 1
                    task.error = f"Task timeout ({self._config.task_timeout_seconds}s)"
                    self._set_status(
                        task,
                        TaskState.FAILED,
                        {"status": "timeout", "attempt": attempt},
                    )
                except Exception as e:
                    self._failure_attempts[task.task_id] = attempt + 1
                    task.error = str(e)
                    self._set_status(
                        task,
                        TaskState.FAILED,
                        {"status": "error", "error": str(e), "attempt": attempt},
                    )

                if attempt < self._config.max_task_retries:
                    task.retries = attempt + 1
                    self._set_status(
                        task,
                        TaskState.RETRYING,
                        {"status": "retrying", "attempt": attempt + 1},
                    )
                    self._set_status(task, TaskState.RUNNING, trace=False)

            # Final status is already FAILED from the last iteration
            self._failed_tasks.append(task.task_id)
            self._set_status(task, TaskState.FAILED, {"status": "failed"})

    def cancel(self) -> None:
        self._cancelled = True
        for task in self._dag.tasks:
            if task.status in (TaskState.PENDING, TaskState.READY, TaskState.RUNNING):
                self._set_status(task, TaskState.CANCELLED, trace=False)

    def _cancel_remaining(self) -> None:
        for task in self._dag.tasks:
            if task.status not in (
                TaskState.SUCCEEDED,
                TaskState.FAILED,
                TaskState.CANCELLED,
            ):
                self._set_status(task, TaskState.CANCELLED, trace=False)

    def check_replan(self) -> ReplanRequest | None:
        failed = list(dict.fromkeys(self._failed_tasks))

        layer_failure = self._find_layer_failure(failed)
        if layer_failure is not None:
            layer_index, failed_in_layer, fail_ratio = layer_failure
            return ReplanRequest(
                reason=(f"DAG layer {layer_index} failure ratio is {fail_ratio:.0%}"),
                failed_tasks=failed,
                trigger="layer_failure_ratio",
                level="layer",
                affected_tasks=failed_in_layer,
                actions=[
                    "replan_current_layer",
                    "add_alternative_tasks",
                    "modify_search_queries",
                ],
                limitations=[
                    f"Layer {layer_index} has failed tasks: "
                    f"{', '.join(failed_in_layer)}"
                ],
            )

        repeatedly_failed = [
            task_id for task_id in failed if self._failure_attempts.get(task_id, 0) >= 2
        ]
        if repeatedly_failed:
            return ReplanRequest(
                reason=f"Tasks failed at least twice: {repeatedly_failed}",
                failed_tasks=failed,
                trigger="repeated_task_failure",
                affected_tasks=repeatedly_failed,
                actions=["retry_with_alternate_queries", "add_alternative_task"],
                limitations=[
                    f"Repeated failures reduced coverage for task {task_id}"
                    for task_id in repeatedly_failed
                ],
            )

        insufficient = self._find_information_insufficient_tasks()
        if insufficient:
            return ReplanRequest(
                reason=f"Tasks reported insufficient information: {insufficient}",
                failed_tasks=failed,
                trigger="information_insufficient",
                affected_tasks=insufficient,
                actions=["modify_search_queries", "add_alternative_task"],
                limitations=[
                    f"Available sources were insufficient for task {task_id}"
                    for task_id in insufficient
                ],
            )

        no_evidence = self._find_zero_evidence_tasks()
        if no_evidence:
            return ReplanRequest(
                reason=f"Tasks produced no evidence: {no_evidence}",
                failed_tasks=failed,
                trigger="zero_evidence",
                affected_tasks=no_evidence,
                actions=["retry_with_alternate_queries", "add_alternative_task"],
                limitations=[
                    f"No usable evidence was found for task {task_id}"
                    for task_id in no_evidence
                ],
            )

        return None

    def _find_layer_failure(
        self, failed: list[str]
    ) -> tuple[int, list[str], float] | None:
        failed_set = set(failed)
        for layer_index, layer in enumerate(self._dag_layers()):
            failed_in_layer = sorted(failed_set.intersection(layer))
            ratio = len(failed_in_layer) / len(layer)
            if len(failed_in_layer) >= 2 and ratio >= 0.4:
                return layer_index, failed_in_layer, ratio
        return None

    def _dag_layers(self) -> list[list[str]]:
        remaining = set(self._dag.task_ids)
        resolved: set[str] = set()
        layers: list[list[str]] = []
        while remaining:
            layer = sorted(
                task_id
                for task_id in remaining
                if self._dag.dependencies(task_id) <= resolved
            )
            if not layer:
                break
            layers.append(layer)
            resolved.update(layer)
            remaining.difference_update(layer)
        return layers

    def _find_information_insufficient_tasks(self) -> list[str]:
        return sorted(
            task.task_id
            for task in self._dag.tasks
            if task.result is not None
            and task.result.get("information_insufficient") is True
        )

    def _find_zero_evidence_tasks(self) -> list[str]:
        tasks: list[str] = []
        for task in self._dag.tasks:
            if task.result is None:
                continue
            evidence = task.result.get("evidence")
            evidence_count = task.result.get("evidence_count")
            if evidence == [] or evidence_count == 0:
                tasks.append(task.task_id)
        return sorted(tasks)

    def _build_timeout_limitations(self) -> list[str]:
        limitations: list[str] = []
        for task in self._dag.tasks:
            if task.status != TaskState.SUCCEEDED:
                limitations.append(
                    f"Task {task.task_id} did not complete before the global timeout"
                )
        return limitations

    def _trace_event(
        self, event_type: TraceEventType, task: TaskNode, data: dict[str, Any]
    ) -> None:
        if self._trace:
            self._trace.log(
                event_type,
                {**data, "task_id": task.task_id},
                task_id=task.task_id,
            )

    def _set_status(
        self,
        task: TaskNode,
        status: TaskState,
        data: dict[str, Any] | None = None,
        *,
        trace: bool = True,
    ) -> None:
        task.status = status
        if trace:
            self._trace_event(
                TraceEventType.TASK_STATE_CHANGED,
                task,
                data or {"status": status.value.lower()},
            )

    def _build_result(self) -> dict[str, Any]:
        succeeded = sum(1 for t in self._dag.tasks if t.status == TaskState.SUCCEEDED)
        failed = sum(1 for t in self._dag.tasks if t.status == TaskState.FAILED)
        skipped = sum(1 for t in self._dag.tasks if t.status == TaskState.SKIPPED)
        cancelled = sum(1 for t in self._dag.tasks if t.status == TaskState.CANCELLED)
        elapsed = time.monotonic() - self._start_time

        return {
            "total": len(self._dag),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "cancelled": cancelled,
            "elapsed_seconds": round(elapsed, 2),
            "failed_tasks": self._failed_tasks,
        }
