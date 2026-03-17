"""
Attention notification system for cross-platform mode support
"""

import json
from typing import Callable, List, Dict, Any, Set
from datetime import datetime
from utils.trace import Trace
from fn2.board import Task, TaskStatus, EscalationType
from config.settings import runtime


class AttentionEvent:
    """Represents an attention event"""

    def __init__(self, task: Task, event_type: str, message: str, timestamp: float = None):
        self.task_id = task.task_id
        self.goal = task.goal
        self.status = task.status.value
        self.escalation_type = task.escalation_type.value if task.escalation_type else None
        self.event_type = event_type
        self.message = message
        self.timestamp = timestamp or datetime.now().timestamp()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'task_id': self.task_id,
            'goal': self.goal,
            'status': self.status,
            'escalation_type': self.escalation_type,
            'event_type': self.event_type,
            'message': self.message,
            'timestamp': self.timestamp
        }


class AttentionNotifier:
    """Cross-platform attention notification system with WebSocket support"""

    def __init__(self):
        self._handlers: List[Callable[[AttentionEvent], None]] = []
        self._event_queue: List[AttentionEvent] = []
        self._max_queue_size = 100
        self._websocket_connections: Set = set()

    def register_handler(self, handler: Callable[[AttentionEvent], None]):
        """Register a handler for attention events"""
        self._handlers.append(handler)

    def unregister_handler(self, handler: Callable[[AttentionEvent], None]):
        """Unregister a handler"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def register_websocket(self, websocket):
        """Register a WebSocket connection for real-time notifications"""
        self._websocket_connections.add(websocket)
        Trace.log("AttentionNotifier", f"WebSocket registered. Total connections: {len(self._websocket_connections)}")

    def unregister_websocket(self, websocket):
        """Unregister a WebSocket connection"""
        self._websocket_connections.discard(websocket)
        Trace.log("AttentionNotifier", f"WebSocket unregistered. Total connections: {len(self._websocket_connections)}")

    async def notify(self, event: AttentionEvent):
        """Notify all registered handlers and WebSocket connections"""
        # Add to queue for polling fallback
        self._add_to_queue(event)

        # Notify all handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                Trace.error("AttentionNotifier", f"Handler error: {e}")

        # Push to all WebSocket connections
        await self._push_to_websockets(event)

    async def _push_to_websockets(self, event: AttentionEvent):
        """Push event to all connected WebSocket clients"""
        if not self._websocket_connections:
            return

        message = json.dumps(event.to_dict())
        disconnected = set()

        for websocket in self._websocket_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                Trace.error("AttentionNotifier", f"WebSocket send error: {e}")
                disconnected.add(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self._websocket_connections.discard(ws)

    def _add_to_queue(self, event: AttentionEvent):
        """Add event to queue (for polling fallback)"""
        self._event_queue.append(event)
        if len(self._event_queue) > self._max_queue_size:
            self._event_queue.pop(0)

    def get_events(self, since: float = None) -> List[Dict[str, Any]]:
        """Get events since a given timestamp (for polling fallback)"""
        if since is None:
            events = self._event_queue
        else:
            events = [e for e in self._event_queue if e.timestamp > since]

        return [e.to_dict() for e in events]

    def clear_events(self):
        """Clear all events from queue"""
        self._event_queue.clear()


# Global notifier instance
_notifier = AttentionNotifier()


def get_notifier() -> AttentionNotifier:
    """Get the global attention notifier instance"""
    return _notifier


def create_attention_handler():
    """Create attention handler for FN2Manager"""
    async def handler(task: Task):
        if task.submitter == "user" or not runtime['auto_fail_system_escalation']:
            if task.status == TaskStatus.ESCL and task.escalation_type == EscalationType.REQ_REFINE:
                # 只通知需要细化的请求，因为这些任务会阻碍任务继续进行
                message = f"Task {task.task_id} needs refinement. Please review."
                event = AttentionEvent(
                    task,
                    event_type='escalation',
                    message=message
                )
                await get_notifier().notify(event)

    return handler


def create_task_status_handler():
    """Create task status change handler for real-time updates"""
    async def handler(task: Task):
        # 为所有任务状态变更发送通知，包括新任务创建
        status_messages = {
            TaskStatus.INIT: f"Task {task.task_id} created: {task.goal}",
            TaskStatus.ACPT: f"Task {task.task_id} accepted",
            TaskStatus.AMBI: f"Task {task.task_id} needs clarification",
            TaskStatus.ANAL: f"Task {task.task_id} analyzed and planned",
            TaskStatus.EXED: f"Task {task.task_id} executed",
            TaskStatus.SYND: f"Task {task.task_id} synthesized",
            TaskStatus.VRFY: f"Task {task.task_id} verified",
            TaskStatus.ESCL: f"Task {task.task_id} escalated for attention",
            TaskStatus.ACK: f"Task {task.task_id} completed"
        }

        message = status_messages.get(task.status, f"Task {task.task_id} status changed to {task.status.value}")
        event = AttentionEvent(
            task,
            event_type='status_change',
            message=message
        )
        await get_notifier().notify(event)

    return handler


def setup_console_handler():
    """Setup console handler for interactive mode"""
    def console_handler(event: AttentionEvent):
        print(f"\n\nATTENTION\n{event.message}\n\n", flush=True)

    get_notifier().register_handler(console_handler)
