from pydantic import BaseModel
from typing import List, Optional


class TaskCreateRequest(BaseModel):
    goal: str


class TaskAcknowledgeRequest(BaseModel):
    issue: str
    result: str


class TaskResponse(BaseModel):
    status: str
    task_id: str


class StatusResponse(BaseModel):
    status: str
    mode: str


class NotificationResponse(BaseModel):
    events: List[dict]
    count: int


class EscalatedTaskResponse(BaseModel):
    task_id: str
    goal: str
    escalation_type: str
    inquiries: List[dict]


class EscalatedTasksResponse(BaseModel):
    tasks: List[EscalatedTaskResponse]
    count: int


class AcknowledgeResponse(BaseModel):
    status: str
    message: str
