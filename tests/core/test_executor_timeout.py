import asyncio

import pytest

from deepresearch.core.dag import DAG
from deepresearch.core.executor import (
    DAGExecutor,
    ExecutorConfig,
    GlobalTimeoutError,
)
from deepresearch.schemas.task import TaskNode, TaskState


def _task(task_id: str, dependencies: list[str] | None = None) -> TaskNode:
    return TaskNode(
        task_id=task_id,
        description=f"Task {task_id}",
        dependencies=dependencies or [],
    )


@pytest.mark.asyncio
async def test_task_timeout_retries_then_fails():
    calls = 0

    async def slow_task(task: TaskNode) -> dict:
        nonlocal calls
        calls += 1
        await asyncio.sleep(1)
        return {}

    dag = DAG([_task("slow")])
    executor = DAGExecutor(
        dag,
        slow_task,
        config=ExecutorConfig(
            task_timeout_seconds=0.01,
            global_timeout_seconds=1,
            max_task_retries=1,
        ),
    )

    result = await executor.run()

    assert calls == 2
    assert result["failed"] == 1
    assert dag.get("slow").status == TaskState.FAILED
    assert dag.get("slow").retries == 1


@pytest.mark.asyncio
async def test_global_timeout_exposes_partial_result_for_forced_synthesis():
    async def task_fn(task: TaskNode) -> dict:
        if task.task_id == "fast":
            return {"evidence": [{"id": "E1"}]}
        await asyncio.sleep(1)
        return {}

    dag = DAG([_task("fast"), _task("slow", ["fast"])])
    executor = DAGExecutor(
        dag,
        task_fn,
        config=ExecutorConfig(
            task_timeout_seconds=2,
            global_timeout_seconds=0.05,
            max_task_retries=0,
        ),
    )

    with pytest.raises(GlobalTimeoutError) as exc_info:
        await executor.run()

    partial = exc_info.value.partial_result
    assert partial["succeeded"] == 1
    assert partial["cancelled"] == 1
    assert partial["degradation_level"] == "global_timeout"
    assert partial["force_synthesis"] is True
    assert partial["limitations"]
    assert dag.get("slow").status == TaskState.CANCELLED


@pytest.mark.asyncio
async def test_cancel_marks_pending_and_running_tasks_cancelled():
    started = asyncio.Event()

    async def slow_task(task: TaskNode) -> dict:
        started.set()
        await asyncio.sleep(1)
        return {}

    dag = DAG([_task("running"), _task("pending", ["running"])])
    executor = DAGExecutor(dag, slow_task)
    run_task = asyncio.create_task(executor.run())
    await started.wait()

    executor.cancel()
    run_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task

    assert dag.get("running").status == TaskState.CANCELLED
    assert dag.get("pending").status == TaskState.CANCELLED
