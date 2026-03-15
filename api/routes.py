from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
from config.settings import runtime
from utils.trace import Trace
from fn2.attention_notifier import get_notifier
from fn2.board import TaskStatus, EscalationType, Acknowledge, ActionType
import os

from api.models import (
    TaskCreateRequest, TaskAcknowledgeRequest, TaskResponse,
    StatusResponse, NotificationResponse, EscalatedTaskResponse,
    EscalatedTasksResponse, AcknowledgeResponse
)


def setup_routes(app: FastAPI):
    """Setup API routes"""
    # Add middleware to log all requests
    @app.middleware("http")
    async def log_requests(request, call_next):
        print(f"Request: {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"Response: {response.status_code}")
        return response

    # Test route
    @app.get("/test")
    async def test():
        return {"message": "Test route works"}

    # API Routes
    @app.get("/api/status", response_model=StatusResponse)
    async def get_status():
        """Get agent status"""
        mode = 'daemon' if runtime.get('daemon', False) else 'web'
        return StatusResponse(status="running", mode=mode)


    @app.get("/api/notifications", response_model=NotificationResponse)
    async def get_notifications(since: Optional[float] = None):
        """Get notifications since a given timestamp"""
        notifier = get_notifier()
        events = notifier.get_events(since)
        Trace.log("Web", f"Returned {len(events)} notifications")
        return NotificationResponse(events=events, count=len(events))


    @app.get("/api/escalated-tasks", response_model=EscalatedTasksResponse)
    async def get_escalated_tasks():
        """Get escalated tasks that need user input"""
        try:
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                return EscalatedTasksResponse(tasks=[], count=0)

            # Get all tasks
            tasks = app.state.fn2_manager.get_board().list_tasks()

            # Filter for escalated tasks that need user input
            pending_tasks = []
            for task in tasks.values():
                # Check if task is escalated and not a result accept escalation
                if task.status == TaskStatus.ESCL and task.escalation_type != EscalationType.RESULT_ACCEPT:
                    # Check if it's a root task or auto_fail_system_escalation is disabled
                    fn2 = app.state.fn2_manager.get_fn2(task.task_id)
                    if fn2 and (fn2.parent is None or not runtime['auto_fail_system_escalation']):
                        # Get inquery actions
                        inquery_actions = []
                        for action in task.actions:
                            if hasattr(action, 'type') and hasattr(action, 'inquery') and action.type == ActionType.INQUERY:
                                inquery_actions.append({
                                    'id': getattr(action, 'id', None),
                                    'inquery': action.inquery
                                })

                        if inquery_actions:
                            pending_tasks.append(EscalatedTaskResponse(
                                task_id=task.task_id,
                                goal=task.goal,
                                escalation_type=task.escalation_type.value if hasattr(task.escalation_type, 'value') else str(task.escalation_type),
                                inquiries=inquery_actions
                            ))

            Trace.log("Web", f"Returned {len(pending_tasks)} escalated tasks")
            return EscalatedTasksResponse(tasks=pending_tasks, count=len(pending_tasks))

        except Exception as e:
            Trace.log("Web", f"Error handling escalated tasks: {str(e)}")
            return EscalatedTasksResponse(tasks=[], count=0)


    @app.post("/api/task", response_model=TaskResponse)
    async def create_task(request: TaskCreateRequest):
        """Create a new task"""
        try:
            Trace.log("Web", f"Creating task with goal: {request.goal}")
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                Trace.log("Web", "fn2_manager not available")
                return TaskResponse(status="error", task_id="")

            Trace.log("Web", "fn2_manager available, spawning fn2")
            fn2 = await app.state.fn2_manager.spawn_fn2("user", request.goal)
            if fn2 is None:
                Trace.log("Web", "spawn_fn2 returned None")
                return TaskResponse(status="error", task_id="")
            Trace.log("Web", f"fn2 spawned successfully, task id: {fn2.task.task_id}")
            Trace.log("Web", f"Received task with goal: '{request.goal}', task id: {fn2.task.task_id}")
            return TaskResponse(status="success", task_id=fn2.task.task_id)
        except Exception as e:
            Trace.log("Web", f"Error creating task: {str(e)}")
            import traceback
            Trace.log("Web", f"Traceback: {traceback.format_exc()}")
            return TaskResponse(status="error", task_id="")


    @app.post("/api/task/{task_id}/acknowledge", response_model=AcknowledgeResponse)
    async def acknowledge_task(task_id: str, request: TaskAcknowledgeRequest):
        """Acknowledge an escalated task"""
        try:
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                return AcknowledgeResponse(status="error", message="FN2Manager not available")

            # Create acknowledge object
            ack = Acknowledge(ack=True, issue=request.issue, result=request.result)

            # Acknowledge task
            await app.state.fn2_manager.get_board().ack_task(task_id, ack)

            Trace.log("Web", f"Task {task_id} acknowledged with issue: '{request.issue}'")
            return AcknowledgeResponse(status="success", message=f'Task {task_id} acknowledged')
        except Exception as e:
            Trace.log("Web", f"Error acknowledging task: {str(e)}")
            return AcknowledgeResponse(status="error", message=f'Error acknowledging task: {str(e)}')

    # Add /api/tasks endpoint for web interface
    @app.get("/api/tasks")
    async def get_tasks():
        """Get all tasks"""
        try:
            Trace.log("Web", "Getting all tasks")
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                Trace.log("Web", "fn2_manager not available")
                return {"tasks": [], "stats": {"total": 0, "running": 0, "pending": 0}}

            Trace.log("Web", "fn2_manager available, getting tasks from board")
            # Get all tasks
            tasks = app.state.fn2_manager.get_board().list_tasks()
            Trace.log("Web", f"Got {len(tasks)} tasks from board")

            # Convert tasks to list
            task_list = []
            for task in tasks.values():
                task_list.append({
                    "task_id": task.task_id,
                    "goal": task.goal,
                    "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
                    "created_at": task.start_time,
                    "updated_at": task.end_time if task.end_time else task.start_time,
                    "parent_id": getattr(task, 'parent_id', None)
                })

            # Calculate stats
            stats = {
                "total": len(task_list),
                "running": len([t for t in task_list if t["status"] == "RUNNING"]),
                "pending": len([t for t in task_list if t["status"] == "ESCL"])
            }

            Trace.log("Web", f"Returning {len(task_list)} tasks with stats: {stats}")
            return {"tasks": task_list, "stats": stats}
        except Exception as e:
            Trace.log("Web", f"Error getting tasks: {str(e)}")
            import traceback
            Trace.log("Web", f"Traceback: {traceback.format_exc()}")
            return {"tasks": [], "stats": {"total": 0, "running": 0, "pending": 0}}
