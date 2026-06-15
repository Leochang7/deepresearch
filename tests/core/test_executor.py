import asyncio
import contextlib

import pytest

from deepresearch.core.dag import DAG
from deepresearch.core.executor import (
    DAGExecutor,
    ExecutorConfig,
    GlobalTimeoutError,
)
from deepresearch.schemas.task import TaskNode, TaskState


def _task(tid: str, deps: list[str] | None = None) -> TaskNode:
    return TaskNode(task_id=tid, description=f"Task {tid}", dependencies=deps or [])


async def _success_fn(task: TaskNode) -> dict:
    return {"task_id": task.task_id, "status": "done"}


async def _fail_fn(task: TaskNode) -> dict:
    raise RuntimeError(f"Task {task.task_id} failed intentionally")


class TestDAGExecutorBasic:
    @pytest.mark.asyncio
    async def test_single_task(self):
        dag = DAG([_task("t1")])
        executor = DAGExecutor(dag, _success_fn)
        result = await executor.run()
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        assert dag.get("t1").status == TaskState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_linear_chain(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"]), _task("t3", ["t2"])])
        executor = DAGExecutor(dag, _success_fn)
        result = await executor.run()
        assert result["succeeded"] == 3
        assert dag.get("t3").status == TaskState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_parallel_tasks(self):
        dag = DAG([_task("t1"), _task("t2"), _task("t3")])
        execution_order: list[str] = []

        async def track_fn(task: TaskNode) -> dict:
            execution_order.append(task.task_id)
            await asyncio.sleep(0.01)
            return {}

        executor = DAGExecutor(dag, track_fn, config=ExecutorConfig(max_concurrency=3))
        result = await executor.run()
        assert result["succeeded"] == 3
        assert len(execution_order) == 3

    @pytest.mark.asyncio
    async def test_diamond_execution(self):
        dag = DAG(
            [
                _task("t1"),
                _task("t2", ["t1"]),
                _task("t3", ["t1"]),
                _task("t4", ["t2", "t3"]),
            ]
        )
        executor = DAGExecutor(dag, _success_fn)
        result = await executor.run()
        assert result["succeeded"] == 4
        assert dag.get("t4").status == TaskState.SUCCEEDED


class TestDAGExecutorFailure:
    @pytest.mark.asyncio
    async def test_failed_task_recorded(self):
        dag = DAG([_task("t1")])
        executor = DAGExecutor(dag, _fail_fn, config=ExecutorConfig(max_task_retries=0))
        result = await executor.run()
        assert result["failed"] == 1
        assert dag.get("t1").status == TaskState.FAILED
        assert "t1" in result["failed_tasks"]

    @pytest.mark.asyncio
    async def test_dependent_skipped_on_failure(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"])])
        executor = DAGExecutor(dag, _fail_fn, config=ExecutorConfig(max_task_retries=0))
        result = await executor.run()
        assert result["failed"] >= 1
        assert dag.get("t2").status == TaskState.SKIPPED

    @pytest.mark.asyncio
    async def test_mixed_dependency_failure_skips_downstream(self):
        async def mixed_fn(task: TaskNode) -> dict:
            if task.task_id == "failed":
                raise RuntimeError("failed intentionally")
            return {}

        dag = DAG(
            [
                _task("succeeded"),
                _task("failed"),
                _task("downstream", ["succeeded", "failed"]),
            ]
        )
        executor = DAGExecutor(
            dag,
            mixed_fn,
            config=ExecutorConfig(max_task_retries=0, global_timeout_seconds=1),
        )

        result = await executor.run()

        assert result["succeeded"] == 1
        assert result["failed"] == 1
        assert result["skipped"] == 1
        assert dag.get("downstream").status == TaskState.SKIPPED

    @pytest.mark.asyncio
    async def test_successful_task_stores_result(self):
        dag = DAG([_task("t1")])
        executor = DAGExecutor(dag, _success_fn)
        await executor.run()
        assert dag.get("t1").result == {"task_id": "t1", "status": "done"}


class TestDAGExecutorRetry:
    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        call_count = {"n": 0}

        async def fail_then_succeed(task: TaskNode) -> dict:
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise RuntimeError("fail")
            return {}

        dag = DAG([_task("t1")])
        executor = DAGExecutor(
            dag, fail_then_succeed, config=ExecutorConfig(max_task_retries=2)
        )
        result = await executor.run()
        assert result["succeeded"] == 1
        assert call_count["n"] == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries_marks_failed(self):
        async def always_fail(task: TaskNode) -> dict:
            raise RuntimeError("always fail")

        dag = DAG([_task("t1")])
        executor = DAGExecutor(
            dag, always_fail, config=ExecutorConfig(max_task_retries=1)
        )
        result = await executor.run()
        assert result["failed"] == 1
        assert dag.get("t1").retries == 1


class TestDAGExecutorTimeout:
    @pytest.mark.asyncio
    async def test_task_timeout(self):
        async def slow_fn(task: TaskNode) -> dict:
            await asyncio.sleep(10)
            return {}

        dag = DAG([_task("t1")])
        executor = DAGExecutor(
            dag,
            slow_fn,
            config=ExecutorConfig(task_timeout_seconds=0.1, max_task_retries=0),
        )
        result = await executor.run()
        assert result["failed"] == 1
        assert dag.get("t1").status == TaskState.FAILED

    @pytest.mark.asyncio
    async def test_global_timeout(self):
        tasks = [_task(f"t{i}", [f"t{i - 1}"] if i > 0 else []) for i in range(10)]

        async def slow_fn(task: TaskNode) -> dict:
            await asyncio.sleep(1.0)
            return {}

        dag = DAG(tasks)
        executor = DAGExecutor(
            dag,
            slow_fn,
            config=ExecutorConfig(
                task_timeout_seconds=5.0,
                global_timeout_seconds=0.2,
                max_concurrency=1,
                max_task_retries=0,
            ),
        )
        with pytest.raises(GlobalTimeoutError):
            await executor.run()


class TestDAGExecutorCancellation:
    @pytest.mark.asyncio
    async def test_cancel(self):
        started = asyncio.Event()

        async def slow_fn(task: TaskNode) -> dict:
            started.set()
            await asyncio.sleep(10)
            return {}

        dag = DAG([_task("t1")])
        executor = DAGExecutor(dag, slow_fn)
        run_task = asyncio.create_task(executor.run())
        await started.wait()
        executor.cancel()
        run_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await run_task
        assert dag.get("t1").status == TaskState.CANCELLED


class TestDAGExecutorConcurrency:
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        concurrent = {"max": 0, "current": 0}

        async def track_fn(task: TaskNode) -> dict:
            concurrent["current"] += 1
            concurrent["max"] = max(concurrent["max"], concurrent["current"])
            await asyncio.sleep(0.05)
            concurrent["current"] -= 1
            return {}

        tasks = [_task(f"t{i}") for i in range(10)]
        dag = DAG(tasks)
        executor = DAGExecutor(dag, track_fn, config=ExecutorConfig(max_concurrency=2))
        await executor.run()
        assert concurrent["max"] <= 2


class TestReplanCheck:
    def test_no_replan_on_success(self):
        dag = DAG([_task("t1")])
        t1 = dag.get("t1")
        t1.status = TaskState.SUCCEEDED
        executor = DAGExecutor(dag, _success_fn)
        assert executor.check_replan() is None

    def test_replan_on_high_failure_ratio(self):
        tasks = [_task(f"t{i}") for i in range(10)]
        dag = DAG(tasks)
        executor = DAGExecutor(
            dag, _success_fn, config=ExecutorConfig(max_task_retries=0)
        )
        executor._failed_tasks = [f"t{i}" for i in range(5)]
        result = executor.check_replan()
        assert result is not None
        assert "40%" in result.reason or "50%" in result.reason

    def test_replan_on_repeated_failure(self):
        dag = DAG([_task("t1")])
        executor = DAGExecutor(dag, _success_fn)
        executor._failed_tasks = ["t1"]
        executor._failure_attempts = {"t1": 2}
        result = executor.check_replan()
        assert result is not None
        assert "t1" in result.failed_tasks
        assert result.trigger == "repeated_task_failure"
