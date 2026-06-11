from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus
from app.schemas.achievement import AchievementRead


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: datetime | None = None
    scheduled_for: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=1440)
    is_focus: bool = False
    category_id: UUID | None = None
    parent_id: UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    deadline: datetime | None = None
    scheduled_for: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=1440)
    is_focus: bool | None = None
    category_id: UUID | None = None
    parent_id: UUID | None = None


class TaskRead(BaseModel):
    id: UUID
    title: str
    description: str | None
    priority: TaskPriority
    status: TaskStatus
    deadline: datetime | None
    scheduled_for: datetime | None
    estimated_minutes: int | None
    is_focus: bool
    completed_at: datetime | None
    category_id: UUID | None
    parent_id: UUID | None

    model_config = ConfigDict(from_attributes=True)


class TaskCompleteResponse(BaseModel):
    task: TaskRead
    achievements: list[AchievementRead]
