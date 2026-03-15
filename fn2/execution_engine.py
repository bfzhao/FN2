"""
Executor in FN2 framework.
"""

import subprocess
from utils.trace import Trace
from typing import Dict, Any, Set, List
from fn2.board import Action, ActionResult, Task, Board, TaskStatus, Acknowledge, ActionType
from fn2.dryrun import DryRun
from config.settings import runtime
from fn2.matcher import Matcher

class ExecutionEngine:
    """
    Executor is responsible for capability matching and execution. it will spawn a new FN2 on need.
    """
    board: Board
    dryrun: DryRun

    def __init__(self, board: Board, dryrun: DryRun = None):
        self.manager = None
        self.board = board
        self.dryrun = dryrun
        self.skills = {}
        self.tools = {}
        self.rag_system = None
        self.pending_tracks: Dict[str, str] = {}

    def set_manager(self, manager: "Fn2Manager"):
        """
        Set the manager for execution engine.
        """
        self.manager = manager

    def register_skill(self, name: str, func):
        """
        Register a skill function.
        """
        self.skills[name] = func

    def register_tool(self, name: str, func):
        """
        Register a tool function.
        """
        self.tools[name] = func

    def set_rag_system(self, rag_callable):
        """
        Set the RAG system callable.
        """
        self.rag_system = rag_callable

    def _handle_rag(self, query: str):
        if not self.rag_system:
            Trace.warn("ExecutionEngine", "RAG system not configured")
            return None

        return self.rag_system(query)

    def _handle_tool(self, tool_spec: Dict[str, Any]):
        name = tool_spec.get("name")
        args = tool_spec.get("args", {})

        if name not in self.tools:
            Trace.warn("ExecutionEngine", f"Tool {name} not registered")
            return None

        return self.tools[name](**args)

    def _handle_skill(self, skill_spec: Dict[str, Any]):
        name = skill_spec.get("name")
        args = skill_spec.get("args", {})

        if name not in self.skills:
            Trace.warn("ExecutionEngine", f"Skill {name} not registered")
            return None

        return self.skills[name](**args)

    def _handle_system_action(self, command: str):
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    def _parent_task_is_blocked(self, task_id: str) -> bool:
        return self.pending_tracks.get(task_id) is not None

    async def on_event(self, task: Task):
        """
        Handle task events from the board.
        """
        Trace.log("Executor", f"notify: {task.task_id} goal={task.goal} status={task.status}")
        if task.status == TaskStatus.ANAL:
            await self.execute(task.task_id, task.goal, task.actions)
        elif task.status == TaskStatus.ACK:
            # some task done, check whether it's block the parent task
            Trace.log("Executor", f"pending_tracks: {self.pending_tracks}")
            pending_id = self.pending_tracks.get(task.task_id)
            if pending_id:
                pending_task = self.board.get_task(pending_id)
                actions = pending_task.actions
                for action in actions:
                    if action.result and action.result.track_id == task.task_id:
                        action.result = ActionResult(
                            pending=None,
                            track_id=task.task_id,
                            success=task.result.success,
                            result=task.result.result
                        )
                        break

                del self.pending_tracks[task.task_id]
                Trace.log("Executor", f"trying to resume this task {pending_id}")
                await self.resume_task(pending_id)
        elif task.status in [TaskStatus.VRFY, TaskStatus.ESCL]:
            # do we need to ack the task?
            if self._parent_task_is_blocked(task.task_id):
                if task.status == TaskStatus.VRFY:
                    Trace.log("Executor", f"task {task.task_id} auto acked as TRUE")
                    await self.board.ack_task(
                        task.task_id,
                        Acknowledge(ack=True, issue="system task completed", result="auto confirm")
                    )
                else:
                    if runtime['auto_fail_system_escalation']:
                        Trace.log("Executor", f"task {task.task_id} auto acked as FALSE")
                        await self.board.ack_task(
                            task.task_id,
                            Acknowledge(ack=False, issue="system task escalated", result="auto abort")
                        )
                    else:
                        Trace.log("Executor",
                            f"skipping auto fail for task {task.task_id} as config disabled")

    async def execute(self, task_id: str, request: str, plans: List[Action]) -> List[Action]:
        """
        Execute a task with the given plans.
        """
        actions = []
        if self.dryrun:
            actions = await self.dryrun.execute(task_id, request, plans)
        else:
            for step in plans:
                Trace.log("Executor", f"step {step}")
                if step.type != ActionType.OPERATION:
                    Trace.error("Executor", f"step {step} type must be OPERATION")
                    continue

                # add decoupling hierarchy
                history = []
                history.append(self.board.get_task(task_id).goal)
                fn2 = self.manager.get_fn2(task_id)
                while fn2 is not None:
                    fn2 = fn2.parent
                    if fn2 is not None:
                        history.append(fn2.task.goal)

                matcher = Matcher(step)
                if matcher.match():
                    success, result = matcher.run()
                    step.result = ActionResult(pending=False, success=success, result=result)
                else:
                    child_fn2 = await self.manager.spawn_fn2("system", step.operation, fn2)
                    subtask = child_fn2.task
                    Trace.log("Executor",
                        f"EXECUTE: operation {step.operation} tracked in subtask {subtask.task_id}")
                    step.result = ActionResult(pending=True, track_id=subtask.task_id)

        depends: Set[str] = set()
        for step in actions:
            if step.result and step.result.pending:
                self.pending_tracks[step.result.track_id] = task_id
                depends.add(step.result.track_id)

        if depends:
            Trace.log("Executor", f"task {task_id} pending due to following depends: {depends}")
        else:
            await self.board.execute_task(task_id, actions)

    async def resume_task(self, task_id: str):
        """
        Resume a task that is pending due to some other tasks.
        """
        if task_id in self.pending_tracks.values():
            Trace.log("Executor",
                f"task {task_id} is going to resume but some is blocking it yet, ignore")
            return

        Trace.log("Executor", f"resume task {task_id}")
        await self.board.execute_task(task_id, self.board.get_task(task_id).actions)
