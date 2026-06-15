import pytest

from deepresearch.core.dag import DAG, CycleError
from deepresearch.schemas.task import TaskNode, TaskState


def _task(tid: str, deps: list[str] | None = None, priority: int = 0) -> TaskNode:
    return TaskNode(
        task_id=tid,
        description=f"Task {tid}",
        dependencies=deps or [],
        priority=priority,
    )


class TestDAGConstruction:
    def test_empty_dag(self):
        dag = DAG()
        assert len(dag) == 0

    def test_add_tasks(self):
        dag = DAG([_task("t1"), _task("t2")])
        assert len(dag) == 2
        assert "t1" in dag.task_ids

    def test_get_task(self):
        dag = DAG([_task("t1")])
        assert dag.get("t1").task_id == "t1"

    def test_dependencies(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"])])
        assert dag.dependencies("t2") == {"t1"}
        assert dag.dependencies("t1") == set()

    def test_dependents(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"]), _task("t3", ["t1"])])
        assert dag.dependents("t1") == {"t2", "t3"}


class TestReadyTasks:
    def test_root_tasks_are_ready(self):
        dag = DAG([_task("t1"), _task("t2")])
        ready = dag.ready_tasks()
        assert len(ready) == 2

    def test_dependent_not_ready(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"])])
        ready = dag.ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

    def test_dep_satisfied_makes_ready(self):
        t1 = _task("t1")
        t1.status = TaskState.SUCCEEDED
        dag = DAG([t1, _task("t2", ["t1"])])
        ready = dag.ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t2"

    def test_sorted_by_priority(self):
        dag = DAG(
            [_task("t1", priority=1), _task("t2", priority=5), _task("t3", priority=3)]
        )
        ready = dag.ready_tasks()
        assert ready[0].task_id == "t2"
        assert ready[1].task_id == "t3"
        assert ready[2].task_id == "t1"

    def test_running_tasks_not_ready(self):
        t1 = _task("t1")
        t1.status = TaskState.RUNNING
        dag = DAG([t1])
        assert dag.ready_tasks() == []

    def test_failed_tasks_not_ready(self):
        t1 = _task("t1")
        t1.status = TaskState.FAILED
        dag = DAG([t1])
        assert dag.ready_tasks() == []


class TestCycleDetection:
    def test_no_cycle(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"]), _task("t3", ["t2"])])
        dag.validate()

    def test_direct_cycle(self):
        dag = DAG([_task("t1", ["t2"]), _task("t2", ["t1"])])
        with pytest.raises(CycleError):
            dag.validate()

    def test_indirect_cycle(self):
        dag = DAG(
            [
                _task("t1", ["t3"]),
                _task("t2", ["t1"]),
                _task("t3", ["t2"]),
            ]
        )
        with pytest.raises(CycleError):
            dag.validate()

    def test_cycle_error_message(self):
        dag = DAG([_task("t1", ["t2"]), _task("t2", ["t1"])])
        with pytest.raises(CycleError, match=r"t1.*t2|t2.*t1"):
            dag.validate()

    def test_missing_dependency_raises(self):
        dag = DAG([_task("t1", ["nonexistent"])])
        with pytest.raises(ValueError, match="nonexistent"):
            dag.validate()


class TestTopologicalOrder:
    def test_linear_order(self):
        dag = DAG([_task("t1"), _task("t2", ["t1"]), _task("t3", ["t2"])])
        order = dag.topological_order()
        assert order.index("t1") < order.index("t2") < order.index("t3")

    def test_parallel_tasks(self):
        dag = DAG([_task("t1"), _task("t2"), _task("t3", ["t1", "t2"])])
        order = dag.topological_order()
        assert order.index("t1") < order.index("t3")
        assert order.index("t2") < order.index("t3")

    def test_diamond(self):
        dag = DAG(
            [
                _task("t1"),
                _task("t2", ["t1"]),
                _task("t3", ["t1"]),
                _task("t4", ["t2", "t3"]),
            ]
        )
        order = dag.topological_order()
        assert order.index("t1") < order.index("t2")
        assert order.index("t1") < order.index("t3")
        assert order.index("t2") < order.index("t4")
        assert order.index("t3") < order.index("t4")
