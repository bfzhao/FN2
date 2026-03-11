import asyncio
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from board import Action, ActionType, ActionResult, TaskResult, Trace
from config import runtime


@dataclass
class TaskDef:
    inquery: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    synthesize: Optional[Dict[str, Any]] = None


@dataclass
class VerificationInfo:
    root_task_status: Optional[str] = None
    root_task_success: Optional[bool] = None
    escalation_type: Optional[str] = None
    decision: Optional[str] = None
    next_suggestion: Optional[str] = None
    result_message_contains: Optional[str] = None
    uncertainty_is_not_none: Optional[bool] = None
    uncertainty_value: Optional[float] = None
    extra_count: Optional[int] = None
    try_count: Optional[int] = None
    depth: Optional[int] = None
    child_tasks: List[Dict[str, Any]] = field(default_factory=list)
    total_children: Optional[int] = None


@dataclass
class RuntimeConfig:
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    name: str
    taskDef: TaskDef
    verification: Optional[VerificationInfo] = None
    runtime_config: Optional[RuntimeConfig] = None


class DryRun:
    def __init__(self):
        self.scenario: Optional[Scenario] = None
        self.analyze_step = 0
        self.execute_step = 0
        self.current_inquery_index = 0
        self._original_runtime_config: Dict[str, Any] = {}

    def load_runtime_config(self):
        if self.scenario and self.scenario.runtime_config and self.scenario.runtime_config.config:
            config_dict = self.scenario.runtime_config.config
            Trace.log("DryRun", f"Loading runtime config: {config_dict}")
            
            for key in config_dict.keys():
                self._original_runtime_config[key] = runtime.get(key)
            
            for key, value in config_dict.items():
                if value is not None:
                    runtime[key] = value
            
            Trace.log("DryRun", f"Runtime config applied: { {k: runtime.get(k) for k in config_dict.keys()} }")

    def restore_runtime_config(self):
        if self._original_runtime_config:
            Trace.log("DryRun", f"Restoring original runtime config: {self._original_runtime_config}")
            for key, value in self._original_runtime_config.items():
                if value is not None:
                    runtime[key] = value
            self._original_runtime_config = {}
            Trace.log("DryRun", "Runtime config restored")

    def _get_current_task_def(self, request: str) -> Optional[TaskDef]:
        """Get TaskDef for current task"""
        if not self.scenario:
            return None
        
        if request == self.scenario.name:
            return self.scenario.taskDef
        
        return self._find_task_def_by_operation(self.scenario.taskDef, request)
    
    def _find_task_def_by_operation(self, task_def: TaskDef, operation: str) -> Optional[TaskDef]:
        for step in task_def.steps:
            if step.get("operation") == operation:
                if not step.get("atom", True) and "taskDef" in step:
                    return step["taskDef"]
                return None
            if not step.get("atom", True) and "taskDef" in step:
                result = self._find_task_def_by_operation(step["taskDef"], operation)
                if result:
                    return result
        return None

    async def analyze(self, request: str) -> List[Action]:
        Trace.log("DryRun", f"run ANALYSIS: request '{request}'")
        steps = []
        if runtime["dryrun"]:
            task_def = self._get_current_task_def(request)
            if task_def:
                Trace.log("DryRun", f"ANALYSIS: scenario '{self.scenario.name}' step {self.analyze_step} for '{request}'")
                if task_def.inquery and task_def.inquery.get("enable"):
                    prompt = task_def.inquery.get("prompt", [])
                    if prompt and self.current_inquery_index < len(prompt):
                        qa = prompt[self.current_inquery_index]
                        steps = [
                            Action(
                                type=ActionType.INQUERY,
                                inquery=qa.get("q", "Question?"),
                            ),
                        ]
                        self.current_inquery_index += 1
                        Trace.log("DryRun", f"ANALYSIS: inquery generated for '{request}': {qa.get('q')}")
                    else:
                        Trace.error("DryRun", f"ANALYSIS: insufficient inquiries for '{request}', please check the config")
                else:
                    for step in task_def.steps:
                        steps.append(Action(
                            type=ActionType.OPERATION,
                            request=request,
                            operation=step.get("operation", "not specified"),
                        ))
                self.analyze_step += 1
            else:
                # generate steps or data inquery based on random choice
                if random.choice([True, False]):
                    n = random.randint(1, 2)
                    Trace.log("DryRun", f"ANALYSIS: random {n} steps generated")
                    for i in range(n):
                        steps.append(Action(
                            type=ActionType.OPERATION,
                            request=request,
                            operation=f"操作{i} for '{request}'",
                        ))
                else:
                    Trace.log("DryRun", f"ANALYSIS: data inquery generated")
                    steps = [
                        Action(
                            type=ActionType.INQUERY,
                            inquery="what is it?",
                        ),
                    ]
            await asyncio.sleep(random.randint(1, 3))
        else:
            Trace.log("DryRun", "ANALYSIS: dryrun not enabled, return empty steps")
        return steps

    async def execute(self, parent_id: str, request: str, steps: List[Action]) -> List[Action]:
        Trace.log("DryRun", f"run EXECUTION: request '{request}'")
        if runtime["dryrun"]:
            task_def = self._get_current_task_def(request)
            if task_def:
                Trace.log("DryRun", f"EXECUTION: scenario '{request}' step {self.execute_step}")
                for i, action in enumerate(steps):
                    step_config = task_def.steps[i]
                    if step_config.get("atom", True):
                        error = step_config.get("error", "")
                        action.result = ActionResult(
                            pending=False,
                            success=step_config.get("success", True),
                            result=step_config.get("error", f"result for '{action.operation}'")
                        )
                    else:
                        from fnfn import FN2
                        child_fn2 = await FN2.spawn("system", action.operation, FN2._task_to_fn2[parent_id])
                        subtask = child_fn2.task
                        Trace.log("DryRun", f"EXECUTE: operation {action.operation} tracked in subtask {subtask.task_id}")
                        action.result = ActionResult(pending=True, track_id=subtask.task_id)

                self.execute_step += 1
                return steps
            else:
                # return result or spawn FN2 based on random choice
                for action in steps:
                    if random.choice([True, False]):
                        from fnfn import FN2
                        child_fn2 = await FN2.spawn("system", action.operation, FN2._task_to_fn2[parent_id])
                        subtask = child_fn2.task
                        Trace.log("DryRun", f"EXECUTE: operation {action.operation} tracked in subtask {subtask.task_id}")
                        action.result = ActionResult(pending=True, track_id=subtask.task_id)
                    else:
                        action.result = ActionResult(
                            pending=False,
                            success=True,
                            result=f"DRYRUN result for '{action.operation}'"
                        )
        else:
            Trace.log("DryRun", "EXECUTION: dryrun not enabled, return steps directly")
        return steps

    async def synthesize(self, request: str, actions: List[Action]) -> TaskResult:
        Trace.log("DryRun", f"run SYNTHESIZE: request '{request}'")
        if runtime["dryrun"]:
            task_def = self._get_current_task_def(request)
            if task_def and task_def.synthesize:
                Trace.log("DryRun", f"SYNTHESIZE: using scenario config for '{request}'")
                synth_config = task_def.synthesize
                return TaskResult(
                    success=synth_config.get("success", True),
                    uncertainty=synth_config.get("uncertainty", 0.0),
                    result=synth_config.get("result", "DryRun result")
                )
            else:
                success = all(action.result and action.result.success for action in actions)
                return TaskResult(
                    success=success,
                    uncertainty=0.0,
                    result="All actions completed" if success else "Some actions failed"
                )
        else:
            Trace.log("DryRun", "SYNTHESIZE: dryrun not enabled, return None")
        return None

    async def human_attention(self, task) -> bool:
        """Handle tasks requiring human attention, return whether to continue"""
        Trace.log("DryRun", f"run HUMAN_ATTENTION: task '{task.goal}'")
        if runtime["dryrun"] and self.scenario:
            # Check if there is inquery configuration
            if self.scenario.taskDef.inquery and self.scenario.taskDef.inquery.get("enable"):
                prompt = self.scenario.taskDef.inquery.get("prompt", [])
                if prompt:
                    # Find matching answer
                    for qa in prompt:
                        if qa.get("q") == task.goal:
                            answer = qa.get("a", "")
                            ack = qa.get("ack", True)
                            print(f"[DryRun] Q: {task.goal}")
                            print(f"[DryRun] A: {answer}")
                            print(f"[DryRun] Ack: {ack}")
                            
                            # Decide whether to confirm task based on ack configuration
                            if task.status == TaskStatus.VRFY and not ack:
                                Trace.log("DryRun", f"task {task.task_id} will be escalated according to scenario config (ack=False)")
                                # Escalate task instead of confirming
                                from board import EscalationType
                                await self.board.escalate_task(task.task_id, EscalationType.RESULT_ARBITRARY)
                                return False
                            return True
        return True
