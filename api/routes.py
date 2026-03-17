import traceback
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from config.settings import runtime
from utils.trace import Trace
from fn2.attention_notifier import get_notifier
from fn2.board import TaskStatus, EscalationType, Acknowledge, ActionType

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
        response = await call_next(request)
        return response

    # WebSocket endpoint for real-time notifications
    @app.websocket("/api/ws/notifications")
    async def websocket_notifications(websocket: WebSocket):
        """WebSocket endpoint for real-time notifications"""
        await websocket.accept()
        Trace.log("Web", f"WebSocket connection accepted from {websocket.client}")

        notifier = get_notifier()
        notifier.register_websocket(websocket)

        try:
            # Keep the connection alive and handle client messages
            while True:
                # Wait for messages from client (can be used for ping/pong or client commands)
                data = await websocket.receive_text()
                Trace.log("Web", f"WebSocket received: {data}")
        except WebSocketDisconnect:
            Trace.log("Web", f"WebSocket disconnected: {websocket.client}")
        except Exception as e:
            Trace.error("Web", f"WebSocket error: {e}")
        finally:
            notifier.unregister_websocket(websocket)

    # API Routes
    @app.get("/api/status", response_model=StatusResponse)
    async def get_status():
        """Get agent status"""
        mode = 'daemon' if runtime.get('daemon', False) else 'web'
        return StatusResponse(status="running", mode=mode)


    @app.get("/api/notifications", response_model=NotificationResponse)
    async def get_notifications(since: Optional[float] = None):
        """Get notifications since a given timestamp (fallback for polling)"""
        notifier = get_notifier()
        events = notifier.get_events(since)
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
                Trace.log("Web", "Failed to spawn fn2")
                return TaskResponse(status="error", task_id="")

            Trace.log("Web", f"fn2 spawned successfully, task_id: {fn2.task.task_id}")
            return TaskResponse(status="success", task_id=fn2.task.task_id)
        except Exception as e:
            Trace.log("Web", f"Error creating task: {str(e)}")
            Trace.log("Web", traceback.format_exc())
            return TaskResponse(status="error", task_id="", message=str(e))


    @app.get("/api/tasks")
    async def get_tasks():
        """Get all tasks"""
        try:
            Trace.log("Web", "Getting all tasks")
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                Trace.log("Web", "fn2_manager not available")
                return {"tasks": [], "count": 0}

            tasks = app.state.fn2_manager.get_board().list_tasks()
            Trace.log("Web", f"Found {len(tasks)} tasks")

            task_list = []
            for task in tasks.values():
                task_data = {
                    "task_id": task.task_id,
                    "goal": task.goal,
                    "status": task.status.value,
                    "submitter": task.submitter,
                    "try_count": task.try_count,
                    "start_time": task.start_time,
                    "end_time": task.end_time
                }

                # Add parent_id if available (for derived tasks)
                fn2 = app.state.fn2_manager.get_fn2(task.task_id)
                if fn2 and fn2.parent and fn2.parent.task:
                    task_data["parent_id"] = fn2.parent.task.task_id

                # Add result if available
                if task.result:
                    task_data["result"] = {
                        "success": task.result.success,
                        "uncertainty": task.result.uncertainty,
                        "result": task.result.result
                    }

                # Add actions if available
                if task.actions:
                    task_data["actions"] = []
                    for action in task.actions:
                        action_data = {"type": action.type.name}
                        if hasattr(action, 'request') and action.request:
                            action_data["request"] = action.request
                        if hasattr(action, 'operation') and action.operation:
                            action_data["operation"] = action.operation
                        if hasattr(action, 'inquery') and action.inquery:
                            action_data["inquery"] = action.inquery
                        if hasattr(action, 'result') and action.result:
                            action_data["result"] = {
                                "success": action.result.success,
                                "result": action.result.result,
                                "observation": action.result.observation,
                                "track_id": getattr(action.result, 'track_id', None)
                            }
                        task_data["actions"].append(action_data)

                task_list.append(task_data)

            return {"tasks": task_list, "count": len(task_list)}
        except Exception as e:
            Trace.log("Web", f"Error getting tasks: {str(e)}")
            Trace.log("Web", traceback.format_exc())
            return {"tasks": [], "count": 0, "error": str(e)}


    @app.get("/api/task/{task_id}")
    async def get_task(task_id: str):
        """Get a specific task"""
        try:
            Trace.log("Web", f"Getting task: {task_id}")
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                Trace.log("Web", "fn2_manager not available")
                return {"error": "fn2_manager not available"}

            task = app.state.fn2_manager.get_board().get_task(task_id)
            if not task:
                Trace.log("Web", f"Task not found: {task_id}")
                return {"error": "Task not found"}

            task_data = {
                "task_id": task.task_id,
                "goal": task.goal,
                "status": task.status.value,
                "submitter": task.submitter,
                "try_count": task.try_count,
                "start_time": task.start_time,
                "end_time": task.end_time
            }

            # Add parent_id if available (for derived tasks)
            fn2 = app.state.fn2_manager.get_fn2(task.task_id)
            if fn2 and fn2.parent and fn2.parent.task:
                task_data["parent_id"] = fn2.parent.task.task_id

            # Add result if available
            if task.result:
                task_data["result"] = {
                    "success": task.result.success,
                    "uncertainty": task.result.uncertainty,
                    "result": task.result.result
                }

            # Add actions if available
            if task.actions:
                task_data["actions"] = []
                for action in task.actions:
                    action_data = {"type": action.type.name}
                    if hasattr(action, 'request') and action.request:
                        action_data["request"] = action.request
                    if hasattr(action, 'operation') and action.operation:
                        action_data["operation"] = action.operation
                    if hasattr(action, 'inquery') and action.inquery:
                        action_data["inquery"] = action.inquery
                    if hasattr(action, 'result') and action.result:
                        action_data["result"] = {
                            "success": action.result.success,
                            "result": action.result.result,
                            "observation": action.result.observation,
                            "track_id": getattr(action.result, 'track_id', None)
                        }
                    task_data["actions"].append(action_data)

            return task_data
        except Exception as e:
            Trace.log("Web", f"Error getting task: {str(e)}")
            Trace.log("Web", traceback.format_exc())
            return {"error": str(e)}


    @app.post("/api/task/{task_id}/acknowledge", response_model=AcknowledgeResponse)
    async def acknowledge_task(task_id: str, request: TaskAcknowledgeRequest):
        """Acknowledge a task with user input"""
        try:
            Trace.log("Web", f"Acknowledging task: {task_id}")
            # Check if fn2_manager is available
            if not hasattr(app.state, 'fn2_manager') or app.state.fn2_manager is None:
                Trace.log("Web", "fn2_manager not available")
                return AcknowledgeResponse(status="error", message="fn2_manager not available")

            # Get the task
            task = app.state.fn2_manager.get_board().get_task(task_id)
            if not task:
                Trace.log("Web", f"Task not found: {task_id}")
                return AcknowledgeResponse(status="error", message="Task not found")

            # Create acknowledge result
            ack_result = Acknowledge(
                ack=True,
                issue=request.issue,
                result=request.result
            )

            # Call ack_task on the board
            await app.state.fn2_manager.get_board().ack_task(task_id, ack_result)

            Trace.log("Web", f"Task acknowledged: {task_id}")
            return AcknowledgeResponse(status="success")
        except Exception as e:
            Trace.log("Web", f"Error acknowledging task: {str(e)}")
            Trace.log("Web", traceback.format_exc())
            return AcknowledgeResponse(status="error", message=str(e))
