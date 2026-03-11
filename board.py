import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Callable, List
import uuid, time

from asyncio.constants import ACCEPT_RETRY_DELAY
from config import runtime
from trace import Trace

class Event(Enum):
    TASK_NEW = "task_new"
    TASK_ACCEPTED = "task_accepted"
    TASK_AMBIGUOUS = "task_ambiguous"
    TASK_ANALYZED = "task_analyzed"
    TASK_EXECUTED = "task_executed"
    TASK_SYNTHESIZED = "task_synthesized"
    TASK_VERIFIED = "task_verified"
    TASK_ESCALATED = "task_escalated"
    TASK_ACKNOWLEDGED = "task_acknowledged"

class TaskStatus(Enum):
    INIT = "initalized"
    ACPT = "accepted"
    AMBI = "ambiguous"
    ANAL = "analyzed"
    EXED = "execution done"
    SYND = "synthesized"
    VRFY = "verified"
    ESCL = "escalated"
    ACK = "acknowledged"

event_map = {
    TaskStatus.INIT: Event.TASK_NEW,
    TaskStatus.ACPT: Event.TASK_ACCEPTED,
    TaskStatus.AMBI: Event.TASK_AMBIGUOUS,
    TaskStatus.ANAL: Event.TASK_ANALYZED,
    TaskStatus.EXED: Event.TASK_EXECUTED,
    TaskStatus.SYND: Event.TASK_SYNTHESIZED,
    TaskStatus.VRFY: Event.TASK_VERIFIED,
    TaskStatus.ESCL: Event.TASK_ESCALATED,
    TaskStatus.ACK: Event.TASK_ACKNOWLEDGED,
}

class ActionType(Enum):
    OPERATION = 1
    INQUERY = 2

class VerifyType(Enum):
    ACCEPT = "ACCEPT"
    ESCALATE = "ESCALATE"
    RETRY = "RETRY"
    
class EscalationType(Enum):
    REQ_REFINE = "REFINE"
    RESULT_ACCEPT = "ACCEPT"
    RESULT_ARBITRARY = "ARBITRARY"
    CAPABILITY_LIMIT = "CAPABILITY_LIMIT"

@dataclass
class TaskResult:
    success: bool = None
    uncertainty: float = None
    result: str = None

@dataclass
class ActionResult:
    observation: str = None
    pending: bool = None
    track_id: str = None
    success: bool = None
    result: str = None

@dataclass
class Action:
    type: ActionType
    request: str = None
    operation: str = None
    inquery: str = None
    result: ActionResult = None

@dataclass
class VerifyResult:
    decision: VerifyType = None
    reason: str = None
    next_suggestion: str = None

@dataclass
class Acknowledge:
    ack: bool = None
    issue: str = None
    result: str = None

class Task:
    def __init__(self, goal: str, submitter: str):
        self.task_id = str(uuid.uuid4())
        self.goal = goal
        self.extras: List[tuple[str, str]] = []
        self.submitter = submitter
        self.try_count = 0
        self.status = TaskStatus.INIT
        self.escalation_type: EscalationType = None
        self.actions: List[Action] = []
        self.result: TaskResult = None
        self.verify = None
        self.acknowledge: Acknowledge = None
        self.start_time = time.time()
        self.end_time = None
        Trace.log("Task", f"created: {self.task_id} goal={self.goal}, status={self.status}")
    
class Board:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.event_listeners: Dict[Event, List[Callable]] = {}
        self._tg = None

    async def __aenter__(self):
        self._tg = asyncio.TaskGroup()
        await self._tg.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._tg.__aexit__(exc_type, exc, tb)

    async def submit_task(self, goal: str, submitter: str = "system"):
        task = Task(goal, submitter)
        self.tasks[task.task_id] = task
        await self._notify_task_status_updated(task)
        return task

    def check_task_status(self, task_id: str, expected_status: List[TaskStatus], next_status: TaskStatus):
        task = self.tasks.get(task_id)
        if not task:
            Trace.log("Task", f"task {task_id} not found")
            return None
        elif task.status not in expected_status:
            Trace.log("Task", f"bad task status of task {task_id}. Expected {expected_status}, but got {task.status}")
            return None
        elif task.status == next_status:
            Trace.log("Task", f"task {task_id} is already {next_status}")
            return None
        
        return task

    async def accept_task(self, task_id: str, clarify = False):
        task = self.check_task_status(task_id, [TaskStatus.INIT, TaskStatus.VRFY], TaskStatus.ACPT)
        if task:
            task.status = TaskStatus.ACPT
            if clarify:
                # redo after refine
                task.acknowledge = None
            else:
                # redo after failure
                task.try_count = task.try_count + 1
            Trace.log("Task", f"accepted: {task.task_id} goal={task.goal}, status={task.status}, try_count={task.try_count}, clarify={clarify}")
            await self._notify_task_status_updated(task)

    async def refine_task(self, task_id: str, actions: List[Action]):
        task = self.check_task_status(task_id, [TaskStatus.ACPT], TaskStatus.AMBI)
        if task:
            task.status = TaskStatus.AMBI
            task.actions = actions
            Trace.log("Task", f"need to refine to fix ambiguous: {task.task_id} goal={task.goal}, status={task.status}, actions={actions}")
            await self._notify_task_status_updated(task)

    async def plan_task(self, task_id: str, actions: List[Action]):
        task = self.check_task_status(task_id, [TaskStatus.ACPT], TaskStatus.ANAL)
        if task:
            task.status = TaskStatus.ANAL
            task.actions = actions
            Trace.log("Task", f"planned: {task.task_id} goal={task.goal}, status={task.status}, actions={actions}")
            await self._notify_task_status_updated(task)

    async def execute_task(self, task_id: str, actions: List[Action]):
        task = self.check_task_status(task_id, [TaskStatus.ANAL], TaskStatus.EXED)
        if task:
            task.status = TaskStatus.EXED
            task.actions = actions
            Trace.log("Task", f"executed: {task.task_id} goal={task.goal}, status={task.status}, actions={actions}")
            await self._notify_task_status_updated(task)

    async def _notify_task_status_updated(self, task: Task):
        event = event_map[task.status]
        if event != None:
            listeners = self.event_listeners.get(event, [])
            for callback in listeners:
                Trace.log("Board", f"Notify event: {event.value} to callback: {callback}")
                if self._tg is None:
                    raise RuntimeError("Board TaskGroup not running")
                self._tg.create_task(callback(task))
        else:
            Trace.log("Task", f"notification event not defined for {task.status}")

    async def synthesis_task(self, task_id: str, result: TaskResult):
        task = self.check_task_status(task_id, [TaskStatus.EXED], TaskStatus.SYND)
        if task:
            task.status = TaskStatus.SYND
            task.end_time = time.time()
            task.result = result
            Trace.log("Task", f"synthesized:: {task.task_id} goal={task.goal}, status={task.status}, success={task.result.success}, uncertainty={task.result.uncertainty}")
            await self._notify_task_status_updated(task)

    async def verify_task(self, task_id: str, verify_result):
        task = self.check_task_status(task_id, [TaskStatus.SYND], TaskStatus.VRFY)
        if task:
            task.status = TaskStatus.VRFY
            task.verify = verify_result
            Trace.log("Task", f"verified: {task.task_id} goal={task.goal}, status={task.status}, verify={verify_result}")
            await self._notify_task_status_updated(task)

    async def escalate_task(self, task_id: str, type: EscalationType):
        task = self.check_task_status(task_id, [TaskStatus.VRFY, TaskStatus.AMBI], TaskStatus.ESCL)
        if task:
            task.status = TaskStatus.ESCL
            task.escalation_type = type
            Trace.log("Task", f"escalated: {task.task_id} goal={task.goal}, status={task.status}, type={type}")
            await self._notify_task_status_updated(task)

    async def ack_task(self, task_id: str, ack_result: Acknowledge):
        task = self.check_task_status(task_id, [TaskStatus.ESCL, TaskStatus.VRFY], TaskStatus.ACK)
        if task:
            task.status = TaskStatus.ACK
            task.acknowledge = ack_result
            task.result = TaskResult(success=ack_result.ack, uncertainty=0.0, result = ack_result.result)
            Trace.log("Task", f"acknowledged: {task.task_id} goal={task.goal}, status={task.status}, ack={ack_result}")
            await self._notify_task_status_updated(task)

    def register_event(self, event: Event, callbacks: List[Callable]):
        if event not in self.event_listeners:
            self.event_listeners[event] = []
        for callback in callbacks:
            self.event_listeners[event].append(callback)

    def list_tasks(self):
        return self.tasks

    def get_task(self, task_id: str) -> Task:
        return self.tasks.get(task_id)
