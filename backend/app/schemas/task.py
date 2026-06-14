from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, computed_field, ConfigDict, Field

from app.core.gamification import calculate_task_xp
from app.models.task import TaskPriority, TaskStatus, TaskVisibility
from app.schemas.achievement import AchievementRead


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: datetime | None = None
    scheduled_for: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=1440)
    is_focus: bool = False
    visibility: TaskVisibility = TaskVisibility.PRIVATE
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
    visibility: TaskVisibility | None = None
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
    visibility: TaskVisibility
    completed_at: datetime | None
    category_id: UUID | None
    parent_id: UUID | None

    @computed_field
    @property
    def estimated_xp(self) -> int:
        return calculate_task_xp(self.priority, self.estimated_minutes)

    model_config = ConfigDict(from_attributes=True)


class TaskCompleteResponse(BaseModel):
    task: TaskRead
    achievements: list[AchievementRead]
    xp_awarded: int = 0
