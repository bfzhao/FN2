# Fratal Negative Feedback Node
from board import Board, Event
from dryrun import DryRun
from analyzer import Analyzer
from execution_engine import ExecutionEngine
from synthesizer import Synthesizer
from controller import Controller
from matcher import Matcher

FRATAL_MAX_DEPTH = 6

class FN2:
    _board: Board = None
    _analyzer: Analyzer = None
    _execution_engine: ExecutionEngine = None
    _synthesizer: Synthesizer = None
    _controller: Controller = None
    _initialized: bool = False
    _task_to_fn2: dict = {}

    @classmethod
    def reset(cls):
        cls._board = None
        cls._analyzer = None
        cls._execution_engine = None
        cls._synthesizer = None
        cls._controller = None
        cls._initialized = False
        cls._task_to_fn2 = {}

    @classmethod
    def init_components(cls, board: Board, dryrun: DryRun, human_attention: callable = None):
        if not cls._initialized:
            cls._board = board
            cls._analyzer = Analyzer(board, dryrun)
            cls._execution_engine = ExecutionEngine(board, dryrun)
            cls._synthesizer = Synthesizer(board, dryrun)
            cls._controller = Controller(board)

            board.register_event(Event.TASK_NEW, [cls._controller.on_event])
            board.register_event(Event.TASK_ACCEPTED, [cls._analyzer.on_event])
            board.register_event(Event.TASK_AMBIGUOUS, [cls._controller.on_event])
            board.register_event(Event.TASK_ANALYZED, [cls._execution_engine.on_event])
            board.register_event(Event.TASK_EXECUTED, [cls._synthesizer.on_event])
            board.register_event(Event.TASK_SYNTHESIZED, [cls._controller.on_event])
            board.register_event(Event.TASK_VERIFIED, [cls._controller.on_event, cls._execution_engine.on_event])
            board.register_event(Event.TASK_ESCALATED, [cls._execution_engine.on_event])
            board.register_event(Event.TASK_ACKNOWLEDGED, [cls._controller.on_event, cls._execution_engine.on_event])

            if human_attention:
                board.register_event(Event.TASK_VERIFIED, [human_attention])
                board.register_event(Event.TASK_ESCALATED, [human_attention])

            cls._initialized = True

    def __init__(self, depth: int = 0, parent: "FN2" = None):
        self.depth = depth
        self.task = None
        self.parent = parent

    @staticmethod
    async def spawn(identifier: str, request: str, parent: "FN2" = None):
        newDepth = 0
        if parent != None:
            newDepth = parent.depth + 1
            if newDepth > FRATAL_MAX_DEPTH:
                # TODO: handle None case when spawn
                return None

        fn2 = FN2(newDepth, parent)
        fn2.task = await FN2._board.submit_task(request, identifier)
        FN2._task_to_fn2[fn2.task.task_id] = fn2
        return fn2
