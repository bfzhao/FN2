"""
Synthesizer in FN2 framework
"""

from typing import List
from utils.trace import Trace
from fn2.llm_synthesizer import LLMSynthesizer
from fn2.board import Task, Board, TaskStatus, Action, TaskResult
from fn2.dryrun import DryRun

class Synthesizer:
    """
    Synthesizer combines action results and provides the final answer.
    """
    board: Board
    llm_synthesizer: LLMSynthesizer
    dryrun: DryRun

    def __init__(self, board: Board, dryrun: DryRun = None):
        self.board = board
        self.dryrun = dryrun
        self.llm_synthesizer = LLMSynthesizer()

    async def synthesize(self, request: str, actions: List[Action]) -> TaskResult:
        """
        Synthesize for the final answer.
        """
        if self.dryrun:
            return await self.dryrun.synthesize(request, actions)
        else:
            return await self.llm_synthesizer.synthesize(actions)

    async def on_event(self, task: Task):
        """
        Event process, start to synthesize task if it was executed.
        """
        Trace.log("Synthesizer", f"notify: {task.task_id} goal={task.goal}, status={task.status}")
        if task.status == TaskStatus.EXED:
            final = await self.synthesize(task.goal, task.actions)
            Trace.log("Synthesizer", f"task {task.task_id} synthesize result={final}")
            await self.board.synthesize_task(task.task_id, final)
