import pytest

from deepresearch.core.state import InvalidStateTransition, TaskStateMachine
from deepresearch.schemas.task import TaskState


class TestLegalTransitions:
    def test_pending_to_ready(self):
        sm = TaskStateMachine()
        sm.transition(TaskState.READY)
        assert sm.state == TaskState.READY

    def test_pending_to_cancelled(self):
        sm = TaskStateMachine()
        sm.transition(TaskState.CANCELLED)
        assert sm.state == TaskState.CANCELLED

    def test_ready_to_running(self):
        sm = TaskStateMachine(initial=TaskState.READY)
        sm.transition(TaskState.RUNNING)
        assert sm.state == TaskState.RUNNING

    def test_ready_to_skipped(self):
        sm = TaskStateMachine(initial=TaskState.READY)
        sm.transition(TaskState.SKIPPED)
        assert sm.state == TaskState.SKIPPED

    def test_running_to_succeeded(self):
        sm = TaskStateMachine(initial=TaskState.RUNNING)
        sm.transition(TaskState.SUCCEEDED)
        assert sm.state == TaskState.SUCCEEDED

    def test_running_to_failed(self):
        sm = TaskStateMachine(initial=TaskState.RUNNING)
        sm.transition(TaskState.FAILED)
        assert sm.state == TaskState.FAILED

    def test_running_to_replanning(self):
        sm = TaskStateMachine(initial=TaskState.RUNNING)
        sm.transition(TaskState.REPLANNING)
        assert sm.state == TaskState.REPLANNING

    def test_failed_to_retrying(self):
        sm = TaskStateMachine(initial=TaskState.FAILED)
        sm.transition(TaskState.RETRYING)
        assert sm.state == TaskState.RETRYING

    def test_failed_to_skipped(self):
        sm = TaskStateMachine(initial=TaskState.FAILED)
        sm.transition(TaskState.SKIPPED)
        assert sm.state == TaskState.SKIPPED

    def test_retrying_to_running(self):
        sm = TaskStateMachine(initial=TaskState.RETRYING)
        sm.transition(TaskState.RUNNING)
        assert sm.state == TaskState.RUNNING

    def test_replanning_to_pending(self):
        sm = TaskStateMachine(initial=TaskState.REPLANNING)
        sm.transition(TaskState.PENDING)
        assert sm.state == TaskState.PENDING

    def test_full_success_path(self):
        sm = TaskStateMachine()
        sm.transition(TaskState.READY)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.SUCCEEDED)
        assert sm.state == TaskState.SUCCEEDED

    def test_retry_path(self):
        sm = TaskStateMachine()
        sm.transition(TaskState.READY)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.FAILED)
        sm.transition(TaskState.RETRYING)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.SUCCEEDED)
        assert sm.state == TaskState.SUCCEEDED

    def test_replan_path(self):
        sm = TaskStateMachine()
        sm.transition(TaskState.READY)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.REPLANNING)
        sm.transition(TaskState.PENDING)
        sm.transition(TaskState.READY)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.SUCCEEDED)
        assert sm.state == TaskState.SUCCEEDED


class TestIllegalTransitions:
    def test_pending_to_running_raises(self):
        sm = TaskStateMachine()
        with pytest.raises(InvalidStateTransition):
            sm.transition(TaskState.RUNNING)

    def test_succeeded_to_any_raises(self):
        for target in TaskState:
            if target == TaskState.SUCCEEDED:
                continue
            sm = TaskStateMachine(initial=TaskState.SUCCEEDED)
            with pytest.raises(InvalidStateTransition):
                sm.transition(target)

    def test_cancelled_is_terminal(self):
        for target in TaskState:
            if target == TaskState.CANCELLED:
                continue
            sm = TaskStateMachine(initial=TaskState.CANCELLED)
            with pytest.raises(InvalidStateTransition):
                sm.transition(target)

    def test_skipped_is_terminal(self):
        for target in TaskState:
            if target == TaskState.SKIPPED:
                continue
            sm = TaskStateMachine(initial=TaskState.SKIPPED)
            with pytest.raises(InvalidStateTransition):
                sm.transition(target)

    def test_running_to_pending_raises(self):
        sm = TaskStateMachine(initial=TaskState.RUNNING)
        with pytest.raises(InvalidStateTransition):
            sm.transition(TaskState.PENDING)

    def test_error_message_contains_states(self):
        sm = TaskStateMachine()
        with pytest.raises(InvalidStateTransition, match=r"PENDING.*RUNNING"):
            sm.transition(TaskState.RUNNING)


class TestStateMachineQuery:
    def test_is_terminal(self):
        assert TaskStateMachine(initial=TaskState.SUCCEEDED).is_terminal
        assert TaskStateMachine(initial=TaskState.CANCELLED).is_terminal
        assert TaskStateMachine(initial=TaskState.SKIPPED).is_terminal
        assert not TaskStateMachine(initial=TaskState.FAILED).is_terminal
        assert not TaskStateMachine(initial=TaskState.RUNNING).is_terminal
        assert not TaskStateMachine(initial=TaskState.PENDING).is_terminal

    def test_allowed_transitions(self):
        sm = TaskStateMachine(initial=TaskState.RUNNING)
        allowed = sm.allowed_transitions()
        assert TaskState.SUCCEEDED in allowed
        assert TaskState.FAILED in allowed
        assert TaskState.PENDING not in allowed
