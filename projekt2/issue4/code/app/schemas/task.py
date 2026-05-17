from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    """Payload for POST /tasks — all fields except owner_id (set from token)."""
    title: str = Field(..., min_length=1, max_length=255, description="Short task name")
    description: Optional[str] = Field(None, description="Longer explanation of the task")
    due_date: Optional[date] = Field(None, description="Deadline, e.g. 2024-12-31")
    priority: TaskPriority = Field(TaskPriority.medium, description="low | medium | high")
    status: TaskStatus = Field(TaskStatus.pending, description="pending | in_progress | done")


class TaskUpdate(BaseModel):
    """
    Payload for PUT /tasks/{id} — every field is optional.
    Only fields that are explicitly provided will be updated (PATCH-style).
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class TaskOut(BaseModel):
    """Task representation returned to the client — safe to expose."""
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[date]
    priority: str
    status: str
    owner_id: int

    class Config:
        orm_mode = True   # allows SQLAlchemy ORM objects to be serialised
