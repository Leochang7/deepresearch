import pytest

from deepresearch.core.dag import DAG
from deepresearch.core.executor import DAGExecutor, ExecutorConfig
from deepresearch.schemas.task import TaskNode


def _task(task_id: str, dependencies: list[str] | None = None) -> TaskNode:
    return TaskNode(
        task_id=task_id,
        description=f"Task {task_id}",
        dependencies=dependencies or [],
    )


async def _success(task: TaskNode) -> dict:
    return {"evidence": [{"task_id": task.task_id}]}


def test_replan_after_repeated_task_failure():
    dag = DAG([_task("research")])
    executor = DAGExecutor(dag, _success)
    executor._failed_tasks = ["research"]
    executor._failure_attempts = {"research": 2}

    request = executor.check_replan()

    assert request is not None
    assert request.trigger == "repeated_task_failure"
    assert request.level == "task"
    assert request.affected_tasks == ["research"]
    assert "retry_with_alternate_queries" in request.actions
    assert request.limitations


def test_replan_when_layer_failure_ratio_reaches_40_percent():
    tasks = [_task(f"task-{index}") for index in range(5)]
    dag = DAG(tasks)
    executor = DAGExecutor(dag, _success)
    executor._failed_tasks = ["task-0", "task-1"]
    executor._failure_attempts = {"task-0": 2, "task-1": 2}

    request = executor.check_replan()

    assert request is not None
    assert request.trigger == "layer_failure_ratio"
    assert request.level == "layer"
    assert request.affected_tasks == ["task-0", "task-1"]
    assert "replan_current_layer" in request.actions


@pytest.mark.asyncio
async def test_replan_when_task_produces_zero_evidence():
    async def no_evidence(task: TaskNode) -> dict:
        return {"evidence": [], "information_insufficient": False}

    dag = DAG([_task("research")])
    executor = DAGExecutor(dag, no_evidence, config=ExecutorConfig())
    await executor.run()

    request = executor.check_replan()

    assert request is not None
    assert request.trigger == "zero_evidence"
    assert request.affected_tasks == ["research"]
    assert request.limitations == ["No usable evidence was found for task research"]


@pytest.mark.asyncio
async def test_replan_when_research_reports_information_insufficient():
    async def insufficient(task: TaskNode) -> dict:
        return {
            "evidence": [{"id": "E1"}],
            "information_insufficient": True,
        }

    dag = DAG([_task("research")])
    executor = DAGExecutor(dag, insufficient)
    await executor.run()

    request = executor.check_replan()

    assert request is not None
    assert request.trigger == "information_insufficient"
    assert request.affected_tasks == ["research"]
    assert "modify_search_queries" in request.actions


@pytest.mark.asyncio
async def test_no_replan_for_successful_task_with_evidence():
    dag = DAG([_task("research")])
    executor = DAGExecutor(dag, _success)
    await executor.run()

    assert executor.check_replan() is None
