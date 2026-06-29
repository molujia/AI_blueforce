"""Task state machine for one task instance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskState(str, Enum):
    CREATED = "CREATED"
    DISPATCHED = "DISPATCHED"
    ACKED = "ACKED"
    RUNNING = "RUNNING"
    WAIT_UPPER = "WAIT_UPPER"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    ABORTED = "ABORTED"


class TransitionError(RuntimeError):
    """Raised when a transition violates SECTION 6."""


TERMINAL_OR_INTERRUPTIBLE = {TaskState.WAIT_UPPER, TaskState.SUCCEEDED, TaskState.FAILED, TaskState.TIMEOUT, TaskState.ABORTED}


@dataclass
class TaskStateMachine:
    task_id: str
    actor_id: str
    state: TaskState = TaskState.CREATED

    def can_submit(self) -> bool:
        return self.state in {TaskState.CREATED, TaskState.WAIT_UPPER, TaskState.SUCCEEDED, TaskState.FAILED, TaskState.TIMEOUT, TaskState.ABORTED}

    def on_submit_sent(self) -> TaskState:
        if not self.can_submit():
            raise TransitionError(f"Submitting a new task is forbidden while state is {self.state.value}.")
        self.state = TaskState.DISPATCHED
        return self.state

    def on_ack(self) -> TaskState:
        self._require(TaskState.DISPATCHED)
        self.state = TaskState.ACKED
        return self.state

    def on_load_error(self, code: str) -> TaskState:
        self._require(TaskState.DISPATCHED)
        if code not in {"BT_LOAD_ERROR", "ACTOR_NOT_FOUND", "PARAM_ERROR", "BT_NOT_FOUND"}:
            raise TransitionError(f"{code} is not a load error transition.")
        self.state = TaskState.FAILED
        return self.state

    def on_running(self) -> TaskState:
        self._require(TaskState.ACKED)
        self.state = TaskState.RUNNING
        return self.state

    def on_return_code(self, code: str) -> TaskState:
        self._require(TaskState.RUNNING)
        if code == "WAIT_UPPER":
            self.state = TaskState.WAIT_UPPER
        elif code == "SUCCESS":
            self.state = TaskState.SUCCEEDED
        elif code in {"UNREACHABLE", "SUBTASK_FAILED"}:
            self.state = TaskState.FAILED
        else:
            raise TransitionError(f"Unsupported runtime return code: {code}")
        return self.state

    def on_timeout(self) -> TaskState:
        self._require(TaskState.RUNNING)
        self.state = TaskState.TIMEOUT
        return self.state

    def on_abort(self) -> TaskState:
        if self.state not in {TaskState.FAILED, TaskState.TIMEOUT, TaskState.WAIT_UPPER, TaskState.RUNNING}:
            raise TransitionError(f"Cannot abort from {self.state.value}.")
        self.state = TaskState.ABORTED
        return self.state

    def _require(self, expected: TaskState) -> None:
        if self.state != expected:
            raise TransitionError(f"Expected {expected.value}, got {self.state.value}.")

