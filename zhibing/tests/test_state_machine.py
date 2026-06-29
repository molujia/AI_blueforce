import unittest
from zhibing.core.task_state_machine import TaskState, TaskStateMachine, TransitionError


class TaskStateMachineTests(unittest.TestCase):
    def test_success_transition_path(self) -> None:
        machine = TaskStateMachine(task_id="task", actor_id="p_4")
        self.assertEqual(machine.on_submit_sent(), TaskState.DISPATCHED)
        self.assertEqual(machine.on_ack(), TaskState.ACKED)
        self.assertEqual(machine.on_running(), TaskState.RUNNING)
        self.assertEqual(machine.on_return_code("SUCCESS"), TaskState.SUCCEEDED)

    def test_running_submit_is_forbidden(self) -> None:
        machine = TaskStateMachine(task_id="task", actor_id="p_4")
        machine.on_submit_sent()
        machine.on_ack()
        machine.on_running()
        with self.assertRaises(TransitionError):
            machine.on_submit_sent()


if __name__ == "__main__":
    unittest.main()
