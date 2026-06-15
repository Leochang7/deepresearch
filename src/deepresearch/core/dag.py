from __future__ import annotations

from collections import defaultdict, deque

from deepresearch.schemas.task import TaskNode, TaskState


class CycleError(Exception):
    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(f"Cycle detected: {' -> '.join(cycle)}")


class DAG:
    def __init__(self, tasks: list[TaskNode] | None = None) -> None:
        self._tasks: dict[str, TaskNode] = {}
        self._children: dict[str, set[str]] = defaultdict(set)
        self._parents: dict[str, set[str]] = defaultdict(set)
        if tasks:
            for task in tasks:
                self.add(task)

    def add(self, task: TaskNode) -> None:
        self._tasks[task.task_id] = task
        for dep_id in task.dependencies:
            self._children[dep_id].add(task.task_id)
            self._parents[task.task_id].add(dep_id)

    def get(self, task_id: str) -> TaskNode:
        return self._tasks[task_id]

    @property
    def task_ids(self) -> list[str]:
        return list(self._tasks.keys())

    @property
    def tasks(self) -> list[TaskNode]:
        return list(self._tasks.values())

    def __len__(self) -> int:
        return len(self._tasks)

    def dependencies(self, task_id: str) -> set[str]:
        return self._parents.get(task_id, set()).copy()

    def dependents(self, task_id: str) -> set[str]:
        return self._children.get(task_id, set()).copy()

    def ready_tasks(self) -> list[TaskNode]:
        ready = []
        for task in self._tasks.values():
            if task.status != TaskState.PENDING:
                continue
            deps = self._parents.get(task.task_id, set())
            if all(self._tasks[dep].status == TaskState.SUCCEEDED for dep in deps):
                ready.append(task)
        return sorted(ready, key=lambda t: t.priority, reverse=True)

    def validate(self) -> None:
        cycle = self._find_cycle()
        if cycle:
            raise CycleError(cycle)

        for task in self._tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self._tasks:
                    raise ValueError(
                        f"Task {task.task_id} depends on unknown task {dep_id}"
                    )

    def topological_order(self) -> list[str]:
        self.validate()
        in_degree: dict[str, int] = {tid: 0 for tid in self._tasks}
        for tid in self._tasks:
            for _dep in self._parents.get(tid, set()):
                in_degree[tid] += 1

        queue: deque[str] = deque(tid for tid, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            tid = queue.popleft()
            order.append(tid)
            for child in self._children.get(tid, set()):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(self._tasks):
            remaining = set(self._tasks) - set(order)
            raise CycleError(list(remaining))

        return order

    def _find_cycle(self) -> list[str] | None:
        WHITE, _GRAY, _BLACK = 0, 1, 2
        color: dict[str, int] = {tid: WHITE for tid in self._tasks}
        parent: dict[str, str | None] = {tid: None for tid in self._tasks}

        for tid in self._tasks:
            if color[tid] == WHITE:
                cycle = self._dfs_cycle(tid, color, parent)
                if cycle:
                    return cycle
        return None

    def _dfs_cycle(
        self,
        start: str,
        color: dict[str, int],
        parent: dict[str, str | None],
    ) -> list[str] | None:
        stack = [start]
        while stack:
            tid = stack[-1]
            if color[tid] == 0:
                color[tid] = 1
                for child in self._children.get(tid, set()):
                    if color[child] == 1:
                        return self._reconstruct_cycle(tid, child, parent)
                    if color[child] == 0:
                        parent[child] = tid
                        stack.append(child)
            else:
                stack.pop()
                if color[tid] == 1:
                    color[tid] = 2
        return None

    def _reconstruct_cycle(
        self, start: str, end: str, parent: dict[str, str | None]
    ) -> list[str]:
        cycle = [end, start]
        current = start
        while current != end:
            current = parent[current]
            cycle.append(current)
        cycle.reverse()
        return cycle

    def __repr__(self) -> str:
        return f"DAG(tasks={len(self._tasks)})"
