"""Module F: state manager for active MVP tasks."""

from __future__ import annotations

from dataclasses import dataclass, field

from zhibing.core.task_state_machine import TaskStateMachine


@dataclass
class StateManager:
    machines: dict[str, TaskStateMachine] = field(default_factory=dict)

    def create(self, *, task_id: str, actor_id: str) -> TaskStateMachine:
        machine = TaskStateMachine(task_id=task_id, actor_id=actor_id)
        self.machines[task_id] = machine
        return machine

    def get(self, task_id: str) -> TaskStateMachine:
        return self.machines[task_id]

