"""
Analyzer in FN2 framework
"""

from typing import List
from utils.trace import Trace
from fn2.llm_analyzer import LLMAnalyzer
from fn2.board import Task, Board, TaskStatus, ActionType, Action
from fn2.dryrun import DryRun

class Analyzer:
    """
    Analyzer frames task and plans the step to solve it.
    """
    comp = "Analyzer"
    board: Board
    dryrun: DryRun
    llm_analyzer: LLMAnalyzer

    def __init__(self, board: Board, dryrun: DryRun = None):
        self.board = board
        self.dryrun = dryrun
        self.llm_analyzer = LLMAnalyzer()

    async def analyze(self, request: str) -> List[Action]:
        """
        Analyze the task goal and generate actions.
        """
        if self.dryrun:
            return await self.dryrun.analyze(request)
        else:
            return await self.llm_analyzer.analyze(request)

    async def on_event(self, task: Task):
        """
        Event process, start to analyze task if it was accepted.
        """
        Trace.log("Analyzer", f"notify: {task.task_id} goal={task.goal} status={task.status}")

        if task.status == TaskStatus.ACPT:
            actions = await self.analyze(task.goal)
            ambiguous = any(a.type == ActionType.INQUERY for a in actions)
            if ambiguous:
                await self.board.refine_task(task.task_id, actions)
            else:
                await self.board.plan_task(task.task_id, actions)
