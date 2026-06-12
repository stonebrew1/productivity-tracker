from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.task import TaskPriority, TaskStatus


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class GroupJoin(BaseModel):
    invite_code: str = Field(min_length=6, max_length=12)


class GroupInvite(BaseModel):
    user_id: UUID


class GroupMemberRead(BaseModel):
    user_id: UUID
    display_name: str | None
    email: str
    avatar_url: str | None
    level: int
    role: str
    joined_at: datetime


class GroupRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    role: str
    invite_code: str | None
    member_count: int
    members: list[GroupMemberRead]


class GroupInvitationRead(BaseModel):
    id: UUID
    group_id: UUID
    group_name: str
    inviter_name: str
    status: str
    created_at: datetime


class GroupTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: datetime | None = None
    assigned_to_id: UUID


class GroupTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    deadline: datetime | None = None
    assigned_to_id: UUID | None = None


class GroupTaskRead(BaseModel):
    id: UUID
    group_id: UUID
    title: str
    description: str | None
    priority: TaskPriority
    status: TaskStatus
    deadline: datetime | None
    created_at: datetime
    completed_at: datetime | None
    assigned_to_id: UUID
    assignee_name: str
    created_by_id: UUID
    can_manage: bool
    can_update_status: bool
