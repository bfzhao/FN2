"""
FN2 manager
"""

from dataclasses import dataclass
from fn2.board import Board, Event, Task
from fn2.dryrun import DryRun
from fn2.analyzer import Analyzer
from fn2.execution_engine import ExecutionEngine
from fn2.synthesizer import Synthesizer
from fn2.controller import Controller

@dataclass
class FN2:
    """
    FN2 instance.
    """
    depth: int
    parent: "FN2" = None
    children: list["FN2"] = None
    task: Task = None

MAX_FRATAL_DEPTH = 6

class FN2Manager:
    """
    FN2 manager manages all instances of FN2 framework.
    """
    def __init__(self, escalate: callable = None, board: Board = None, dryrun: DryRun = None):
        self._initialized = False
        self._root_fn2 = []
        self.board = board if board else Board()
        self.dryrun = dryrun
        self.analyzer = Analyzer(self.board, self.dryrun)
        self.execution_engine = ExecutionEngine(self.board, self.dryrun)
        self.synthesizer = Synthesizer(self.board, self.dryrun)
        self.controller = Controller(self.board)
        self.task_to_fn2 = {}

        self.execution_engine.set_manager(self)
        if self.dryrun:
            self.dryrun.set_manager(self)

        if not self._initialized:
            self.board.register_event(Event.TASK_NEW, [self.controller.on_event])
            self.board.register_event(Event.TASK_ACCEPTED, [self.analyzer.on_event])
            self.board.register_event(Event.TASK_AMBIGUOUS, [self.controller.on_event])
            self.board.register_event(Event.TASK_ANALYZED, [self.execution_engine.on_event])
            self.board.register_event(Event.TASK_EXECUTED, [self.synthesizer.on_event])
            self.board.register_event(Event.TASK_SYNTHESIZED, [self.controller.on_event])
            self.board.register_event(Event.TASK_VERIFIED, [
                self.controller.on_event,
                self.execution_engine.on_event])
            self.board.register_event(Event.TASK_ESCALATED, [self.execution_engine.on_event])
            self.board.register_event(Event.TASK_ACKNOWLEDGED, [
                self.controller.on_event,
                self.execution_engine.on_event])

            if escalate:
                self.board.register_event(Event.TASK_VERIFIED, [escalate])
                self.board.register_event(Event.TASK_ESCALATED, [escalate])

            self._initialized = True

    def get_board(self) -> Board:
        """
        Get the board instance.
        """
        return self.board

    def get_dryrun(self) -> DryRun:
        """
        Get the dryrun instance.
        """
        return self.dryrun

    def get_fn2(self, task_id: str) -> dict:
        """
        Get the FN2 instance for the task.
        """
        return self.task_to_fn2.get(task_id, None)

    def get_root_fn2(self) -> list[FN2]:
        """
        Get the root FN2 instance.
        """
        return self._root_fn2

    async def spawn_fn2(self, identifier: str, request: str, parent: FN2 = None):
        """
        Spawn a new FN2 instance.
        """
        new_depth = 0
        if parent is not None:
            new_depth = parent.depth + 1
            if new_depth > MAX_FRATAL_DEPTH:
                return None

        fn2 = FN2(new_depth, parent)
        # Initialize children if not set
        if fn2.children is None:
            fn2.children = []
        if parent is not None:
            if parent.children is None:
                parent.children = []
            parent.children.append(fn2)
        else:
            fn2.children = []

        fn2.task = await self.board.submit_task(request, identifier)
        self.task_to_fn2[fn2.task.task_id] = fn2
        if new_depth == 0:
            self._root_fn2.append(fn2)
        return fn2
