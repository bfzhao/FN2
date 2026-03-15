"""
Interactive mode for FN2 Agent - Console-based user interaction
"""

import asyncio
from utils.trace import Trace
from aioconsole import ainput
from fn2.board import Acknowledge, TaskStatus, ActionType, EscalationType
from config.settings import runtime
from fn2.fn2_manager import FN2, FN2Manager


class InteractiveMode:
    """Interactive console mode for FN2 Agent"""

    def __init__(self, fn2_manager: FN2Manager):
        self.fn2_manager = fn2_manager
        self.number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
                              "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    def show_help(self):
        """Show available commands."""
        print("Available commands:")
        print("  '/exit' to exit the program")
        print("  '/q' to exit the program")
        print("  '/h' to show this message")
        print("  '/ls' to list all tasks")
        print("  '/trace' to show trace config")
        print("  '/trace <component|all> <on|off>' to enable/disable tracing")
        print("  '/dump <id>' to dump the task with the given id")
        print("  '/p <id>' to process escalated task")

    def dump_fn2_tree(self, fn2: FN2 = None, level: int = 0,
                      parent_action_indent: str = "", is_root: bool = False):
        """Dump the FN2 tree structure."""
        if fn2 is None:
            fn2_roots = self.fn2_manager.get_root_fn2()
            for fn2_root in fn2_roots:
                self.dump_fn2_tree(fn2_root, is_root=True)
            return

        if parent_action_indent:
            indent = parent_action_indent + "  "
        else:
            indent = "  " * level

        if fn2.task:
            task = fn2.task
            status_str = f"({task.status.value})"
            if task.status == TaskStatus.ESCL and task.escalation_type:
                status_str = f"({task.status.value} - {task.escalation_type.value})"
            if task.status == TaskStatus.ACK:
                status_str = f"({task.status.value} - {task.acknowledge.ack})"

            if is_root:
                print(f"{indent}\033[1;32m🎯 [{task.task_id}]: goal=\"{task.goal}\" {status_str}\033[0m")
            else:
                print(f"{indent}\033[1;34m🧩 [{task.task_id}]: goal=\"{task.goal}\" {status_str}\033[0m")

            for i, action in enumerate(task.actions, 1):
                emoji_num = self.number_emojis[i - 1] if i <= len(self.number_emojis) else f"{i}."
                action_indent = indent + "  "
                if action.type == ActionType.OPERATION:
                    step_str = f"{action_indent}{emoji_num}  {action.operation}"
                    if action.result:
                        if action.result.pending:
                            step_str += f" -> Pending (track_id: {action.result.track_id})"
                        else:
                            result_str = "success" if action.result.success else "failure"
                            step_str += f" -> {result_str}"
                            if action.result.result:
                                step_str += f": {action.result.result}"
                    print(step_str)

                    if action.result.track_id:
                        child = self.fn2_manager.get_fn2(action.result.track_id)
                        self.dump_fn2_tree(child, level + 1, action_indent)
                elif action.type == ActionType.INQUERY:
                    step_str = f"{action_indent}{emoji_num} Inquery: {action.inquery}"
                    if action.result and action.result.result:
                        step_str += f" -> Answer: {action.result.result}"
                    print(step_str)
        else:
            if is_root:
                print(f"{indent}\033[1;32m🎯 FN2[{fn2.identifier}]: no task\033[0m")
            else:
                print(f"{indent}\033[1;34m🧩 FN2[{fn2.identifier}]: no task\033[0m")

    async def handle_command(self, cmd: str) -> bool:
        """Handle user commands. Returns False to exit, True to continue."""
        if cmd in ["/exit", "/q"]:
            return False

        if cmd == "/h":
            self.show_help()
        elif cmd == "/ls":
            self.dump_fn2_tree()
        elif cmd.startswith("/trace"):
            await self._handle_trace_command(cmd)
        elif cmd.startswith("/dump"):
            await self._handle_dump_command(cmd)
        elif cmd.startswith("/p"):
            await self._handle_process_command()
        else:
            self.show_help()

        return True

    async def _handle_trace_command(self, cmd: str):
        """Handle trace command."""
        parts = cmd.split()
        if len(parts) == 3:
            component = parts[1].lower()
            if component == "all":
                for comp in runtime["trace"]:
                    runtime["trace"][comp] = parts[2].lower() == "on"
                enable = "enabled" if parts[2].lower() == "on" else "disabled"
                print(f"trace {enable} on all component")
            elif component in runtime["trace"]:
                runtime["trace"][component] = parts[2].lower() == "on"
                enable = "enabled" if runtime['trace'][component] else "disabled"
                print(f"trace {enable} on {component}")
            else:
                self.show_help()
        elif len(parts) == 1:
            print("All trace config:")
            for component in runtime["trace"]:
                print(f"  {component}: {'on' if runtime['trace'][component] else 'off'}")
        else:
            self.show_help()

    async def _handle_dump_command(self, cmd: str):
        """Handle dump command."""
        parts = cmd.split()
        if len(parts) == 2:
            task_id = parts[1]
            task = self.fn2_manager.get_board().get_task(task_id)
            if task:
                fn2 = self.fn2_manager.get_fn2(task.task_id)
                print("FN2 Dump:")
                print(f"  depth: {fn2.depth}")
                print(f"  parent: {fn2.parent}")
                print(f"  Task Id: {task.task_id}")
                print(f"    Goal: {task.goal}")
                print(f"    Extras: {task.extras}")
                print(f"    Submitter: {task.submitter}")
                print(f"    actions: {task.actions}")
                print(f"    result: {task.result}")
                print(f"    verify: {task.verify}")
                print(f"    acknowledge: {task.acknowledge}")
                print(f"    Status: {task.status.value}")
                print(f"    Esalation Type: {task.escalation_type.value}")
            else:
                print(f"Task {task_id} not found")
        else:
            self.show_help()

    async def _handle_process_command(self):
        """Handle process escalated tasks command."""
        tasks = self.fn2_manager.get_board().list_tasks()
        pending_tasks = [task for task in tasks.values() if
                         task.status == TaskStatus.ESCL and
                         task.escalation_type != EscalationType.RESULT_ACCEPT and
                         (self.fn2_manager.get_fn2(task.task_id).parent is None
                          or not runtime['auto_fail_system_escalation'])]

        print(f"There are {len(pending_tasks)} tasks escalated.")
        for task in pending_tasks:
            print(f"{task.goal} ({task.task_id}):")
            actions = task.actions
            for action in actions:
                if action.type != ActionType.INQUERY:
                    Trace.error("Main", f"non-inquery action {action} found, ignored")
                    continue

                print(f"  Issue: {action.inquery}")
                response = await ainput("  Please input your response: ")
                ack = Acknowledge(ack=True, issue=action.inquery, result=response)
                await self.fn2_manager.get_board().ack_task(task.task_id, ack)
                print(f"Task {task.task_id} acknowledged\n")

    async def read_request(self, prompt: str) -> tuple[bool, str]:
        """Read user request from console."""
        while True:
            user_input = await ainput(prompt)
            if user_input.strip() == "":
                continue

            command = user_input.lower().strip()
            if command.startswith("/"):
                if not await self.handle_command(command):
                    return True, None
            else:
                return False, user_input.strip()

    async def run(self):
        """Run interactive mode."""
        print("=== Welcome to FN2 Agent ===")
        try:
            while True:
                exit_flag, goal = await self.read_request(
                    "What do you want to do? (/h for help) ")
                if exit_flag:
                    break

                fn2 = await self.fn2_manager.spawn_fn2("user", goal)
                Trace.log("Main", f"FN2 created with goal '{goal}', task id: {fn2.task.task_id}")
        except (KeyboardInterrupt, asyncio.CancelledError):
            Trace.log("Main", "Break to exit...")
        finally:
            self.dump_fn2_tree()
