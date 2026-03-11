import asyncio
import sys
from aioconsole import ainput
from board import Board, Acknowledge, Task, TaskStatus, ActionType, EscalationType
from config import runtime
from trace import Trace
from fnfn import FN2
from dryrun import DryRun


async def human_attention(task: Task):
    if task.submitter == "user" or not runtime['auto_fail_system_escalation']:
        if task.status == TaskStatus.ESCL and task.escalation_type == EscalationType.REQ_REFINE:
            Trace.log("Main", f"\n\nATTENTION\nTask {task.task_id} escalated. Please review and process.\n\n")
        elif task.status == TaskStatus.VRFY:
            Trace.log("Main", f"Task {task.task_id} verified. ready to be check and accepted")
    # user need to ack those message so that the procedure can continue

def help():
    print("Available commands:")
    print("  '/exit' to exit the program")
    print("  '/h' to show this message")
    print("  '/ls' to list all tasks")
    print("  '/trace' to show trace confid")
    print("  '/trace <component|all> <on|off>' to enable/disable tracing")
    print("  '/dump <id>' to dump the task with the given id")
    print("  '/p <id>' to process esclated task")

def dump_fn2_tree(fn2: FN2 = None, level: int = 0, parent_action_indent: str = ""):
    # Emoji number mapping
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    if fn2 is None:
        root_nodes = [fn2_node for fn2_node in FN2._task_to_fn2.values() if fn2_node.parent is None]
        if not root_nodes:
            print("No FN2 node found.")
            return
        
        for root in root_nodes:
            dump_fn2_tree(root)
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

        print(f"{indent}📦 [{task.task_id}]: goal=\"{task.goal}\" {status_str}")
        
        for i, action in enumerate(task.actions, 1):
            emoji_num = number_emojis[i - 1] if i <= len(number_emojis) else f"{i}."
            action_indent = indent + "  "
            if action.type == ActionType.OPERATION:
                step_str = f"{action_indent}{emoji_num} {action.operation}"
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
                    child = FN2._task_to_fn2[action.result.track_id]
                    dump_fn2_tree(child, level + 1, action_indent)
            elif action.type == ActionType.INQUERY:
                step_str = f"{action_indent}{emoji_num} Inquery: {action.inquery}"
                if action.result and action.result.result:
                    step_str += f" -> Answer: {action.result.result}"
                print(step_str)
    else:
        print(f"{indent}📦 FN2[{fn2.identifier}]: no task")
    
async def handle_command(cmd: str):
    if cmd == "/exit" or cmd == "/q":
        return False

    if cmd == "/h":
        help()
    elif cmd == "/ls":
        dump_fn2_tree()
    elif cmd.startswith("/trace"):
        parts = cmd.split()
        if len(parts) == 3:
            component = parts[1].lower()
            if component == "all":
                for comp in runtime["trace"]:
                    runtime["trace"][comp] = parts[2].lower() == "on"
                print(f"trace on all {'enabled' if parts[2].lower() == "on" else 'disabled'}")
            elif component in runtime["trace"]:
                runtime["trace"][component] = parts[2].lower() == "on"
                print(f"trace on {component} {'enabled' if runtime['trace'][component] else 'disabled'}")
            else:
                help()
        elif len(parts) == 1:
            print("All trace config:")
            for component in runtime["trace"]:
                print(f"  {component}: {'on' if runtime['trace'][component] else 'off'}")
        else:
            help()
    elif cmd.startswith("/dump"):
        parts = cmd.split()
        if len(parts) == 2:
            task_id = parts[1]
            task = FN2._board.get_task(task_id)
            if task:
                fn2 = FN2._task_to_fn2[task.task_id]
                print(f"FN2 Dump:")
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
            help()
    elif cmd.startswith("/p"):
        tasks = FN2._board.list_tasks()
        pending_tasks = [task for task in tasks.values() if 
            task.status == TaskStatus.ESCL and 
            task.escalation_type != EscalationType.RESULT_ACCEPT and
            (FN2._task_to_fn2[task.task_id].parent is None or not runtime['auto_fail_system_escalation'])]

        print(f"There are {len(pending_tasks)} tasks escalated.")
        for task in pending_tasks:
            print(f"{task.goal} ({task.task_id}):")
            actions = task.actions
            ack: Acknowledge = None
            for action in actions:
                if action.type != ActionType.INQUERY:
                    Trace.log("Main", f"ALERT: found non-inquery action {action} in process phase, ignored")
                    continue

                print(f"  Issue: {action.inquery}")
                response = await ainput("  Please input your response: ")
                ack = Acknowledge(ack=True, issue=action.inquery, result=response)
                await FN2._board.ack_task(task.task_id, ack)
                print(f"Task {task.task_id} acknowledged\n")
    else:
        help()
    
    return True

async def read_request(prompt: str) -> tuple[bool, str]:
    while True:
        user_input = await ainput(prompt)
        if user_input.strip() == "":
            continue

        command = user_input.lower().strip()
        if command.startswith("/"):
            if not await handle_command(command):
                return True, None
        else:
            return False, user_input.strip()

async def main():
    board = Board()
    dryrun = DryRun() if runtime["dryrun"] else None
    FN2.init_components(board, dryrun, human_attention)

    async with board:
        print("=== Welcome to FN2 Agent ===")
        try:
            while True:
                exitFlag, goal = await read_request("What do you want to do? (/h for help) ")
                if exitFlag:
                    break

                fn2 = await FN2.spawn("user", goal)
                Trace.log("Main", f"FN2 created with goal '{goal}', task id: {fn2.task.task_id}")
        except (KeyboardInterrupt, asyncio.CancelledError):
            Trace.log("Main", "Break to exit...")
        finally:
            Trace.log("Main", "safe exited")

if __name__ == "__main__":
    try:
        asyncio.run(main())
        dump_fn2_tree()
    except KeyboardInterrupt:
        sys.exit(0)
