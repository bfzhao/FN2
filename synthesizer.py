from typing import List
from llm_synthesizer import LLMSynthesizer
from board import Task, Board, TaskStatus, Action, TaskResult
from dryrun import DryRun
from trace import Trace

class Synthesizer:
    board: Board
    llm_synthesizer: LLMSynthesizer
    dryrun: DryRun

    def __init__(self, board: Board, dryrun: DryRun = None):
        self.board = board
        self.dryrun = dryrun
        self.llm_synthesizer = LLMSynthesizer()

    async def synthesize(self, request: str, actions: List[Action]) -> TaskResult:
        if self.dryrun:
            return await self.dryrun.synthesize(request, actions)
        else:
            return await self.llm_synthesizer.synthesize(actions)

    async def on_event(self, task: Task):
        Trace.log("Synthesizer", f"notify: {task.task_id} goal={task.goal}, status={task.status}")
        if task.status == TaskStatus.EXED:
            final = await self.synthesize(task.goal, task.actions)
            Trace.log("Synthesizer", f"task {task.task_id} synthesize result={final}")
            await self.board.synthesis_task(task.task_id, final)
