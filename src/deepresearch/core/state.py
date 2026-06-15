from __future__ import annotations

from deepresearch.schemas.task import TaskState

# Legal transitions: state -> set of reachable states
_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.READY, TaskState.CANCELLED},
    TaskState.READY: {TaskState.RUNNING, TaskState.SKIPPED, TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskState.SUCCEEDED,
        TaskState.FAILED,
        TaskState.CANCELLED,
        TaskState.REPLANNING,
    },
    TaskState.FAILED: {TaskState.RETRYING, TaskState.SKIPPED, TaskState.CANCELLED},
    TaskState.RETRYING: {TaskState.RUNNING},
    # Terminal states
    TaskState.SUCCEEDED: set(),
    TaskState.SKIPPED: set(),
    TaskState.CANCELLED: set(),
    TaskState.REPLANNING: set(),
}


class InvalidStateTransition(Exception):
    def __init__(self, current: TaskState, target: TaskState) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Invalid state transition: {current.value} -> {target.value}")


class TaskStateMachine:
    def __init__(self, initial: TaskState = TaskState.PENDING) -> None:
        self._state = initial

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return len(_TRANSITIONS[self._state]) == 0

    def allowed_transitions(self) -> set[TaskState]:
        return _TRANSITIONS[self._state].copy()

    def can_transition(self, target: TaskState) -> bool:
        return target in _TRANSITIONS[self._state]

    def transition(self, target: TaskState) -> TaskState:
        if target not in _TRANSITIONS[self._state]:
            raise InvalidStateTransition(self._state, target)
        self._state = target
        return self._state
