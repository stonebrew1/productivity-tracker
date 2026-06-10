from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.task_event import TaskEventType


class TaskEventRead(BaseModel):
    id: UUID
    event_type: TaskEventType
    task_id: UUID
    task_title: str
    changes: dict
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskEventPage(BaseModel):
    items: list[TaskEventRead]
    total: int
    limit: int
    offset: int
