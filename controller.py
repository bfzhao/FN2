"""
Controller in FN2 framework.
"""
from typing import Dict
from trace import Trace
from board import Task, Board, TaskStatus, EscalationType, VerifyResult, VerifyType
from config import nfn, runtime


class Controller:
    """
    Controller bridges the human and the FN2.
    """
    board: Board
    ambiguous_tasks: Dict[str, Task]

    def __init__(
        self,
        board: Board,
    ):
        self.board = board
        self.max_retries = nfn["max_iterations"]
        self.uncertainty_threshold = nfn["uncertainty_threshold"]
        self.ambiguous_tasks = {}

    async def on_event(self, task: Task):
        """
        Handle the event from the board.
        """
        Trace.log("Controller", f"notify: {task.task_id} goal={task.goal} status={task.status}")
        if task.status == TaskStatus.INIT:
            Trace.log("Controller", f"accept new task: {task.task_id} goal={task.goal} submitter={task.submitter}")
            await self.board.accept_task(task.task_id)
        elif task.status == TaskStatus.AMBI:
            Trace.log("Controller", f"escalate ambiguous task: {task.task_id} goal={task.goal}")
            self.ambiguous_tasks[task.task_id] = task
            await self.board.escalate_task(task.task_id, EscalationType.REQ_REFINE)
        elif task.status == TaskStatus.SYND:
            Trace.log("Controller", f"handle synthesized task: {task.task_id} goal={task.goal}")
            result = self.verify(task)
            await self.board.verify_task(task.task_id, result)
            if result.decision == VerifyType.ACCEPT:
                Trace.log("Controller",
                    f"task success and verified: {task.task_id} goal={task.goal} reason={result}")
            elif result.decision == VerifyType.RETRY:
                Trace.log("Controller",
                    f"task failed and need retry: {task.task_id} goal={task.goal} reason={result}")
                await self.board.accept_task(task.task_id)
            elif result.decision == VerifyType.ESCALATE:
                Trace.log("Controller",
                    f"task failed and escalated: {task.task_id} goal={task.goal} reason={result}")
                ## TODO: fix the hardcode message
                escalation_type = EscalationType.CAPABILITY_LIMIT if "Capability limit" in result.reason else EscalationType.RESULT_ARBITRARY
                await self.board.escalate_task(task.task_id, escalation_type)
            else:
                Trace.error("Controller",
                    f"unknown verify decision: {task.task_id} goal={task.goal}, reason={result.reason}")
        elif task.status == TaskStatus.ACK:
            Trace.log("Controller",
                f"task acknowledged and finished: {task.task_id} goal={task.goal}")
            if task.task_id in self.ambiguous_tasks:
                Trace.log("Controller",
                    f"ACK: found {task.task_id} in ambiguous_tasks, remove and reaccept the updated task")
                del self.ambiguous_tasks[task.task_id]

                if task.acknowledge.ack and task.escalation_type == EscalationType.REQ_REFINE and task.submitter != "system":
                    Trace.log("Controller", 
                        f"task {task.task_id} ACK passed, reaccept the task and try again")
                    task.extras.append((task.acknowledge.issue, task.acknowledge.result))
                    task.status = TaskStatus.INIT
                    task.actions = []
                    task.result = None
                    task.acknowledge = None
                    await self.board.accept_task(task.task_id, clarify=True)
            else:
                Trace.log("Controller", f"ACK: {task.task_id} NOT found in ambiguous_tasks, DONE")

    def verify(
        self,
        task: Task,
    ) -> VerifyResult:
        """
        Verify the task result.
        """
        if task.result.success:
            return VerifyResult(
                decision=VerifyType.ACCEPT,
                reason="Success criteria satisfied",
                next_suggestion=None
            )

        if task.result and task.result.result and "Capability limit reached" in task.result.result:
            return VerifyResult(
                decision=VerifyType.ESCALATE,
                reason="Capability limit exceeded",
                next_suggestion="eleberate the request"
            )

        if task.try_count >= self.max_retries:
            return VerifyResult(
                decision=VerifyType.ESCALATE,
                reason="Max retries exceeded",
                next_suggestion="eleberate the request"
            )

        if task.result.uncertainty > self.uncertainty_threshold:
            return VerifyResult(
                decision=VerifyType.ESCALATE,
                reason="High uncertainty",
                next_suggestion="clear the uncertainty"
            )

        if runtime['auto_retry_tasks']:
            return VerifyResult(
                decision=VerifyType.RETRY,
                reason="Failure with manageable uncertainty",
                next_suggestion="auto retry"
            )

        return VerifyResult(
            decision=VerifyType.ESCALATE,
            reason="Auto retry disabled",
            next_suggestion="manual retry"
        )
