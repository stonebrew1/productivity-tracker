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
    milestone_id: UUID | None = None


class GroupTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    deadline: datetime | None = None
    assigned_to_id: UUID | None = None
    milestone_id: UUID | None = None


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
    milestone_id: UUID | None
    milestone_title: str | None
    can_manage: bool
    can_update_status: bool


class GroupMilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    target_date: datetime | None = None


class GroupMilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    target_date: datetime | None = None


class GroupMilestoneRead(BaseModel):
    id: UUID
    group_id: UUID
    title: str
    description: str | None
    target_date: datetime | None
    created_at: datetime
    task_count: int
    completed_task_count: int
    progress_percent: int
    is_complete: bool
    can_manage: bool


class GroupLeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    display_name: str
    avatar_url: str | None
    group_xp: int
    completed_tasks: int
    contribution_streak: int
    is_current_user: bool


class GroupRewardRead(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    reason: str
    amount: int
    awarded_at: datetime


class GroupProgressRead(BaseModel):
    total_group_xp: int
    completed_tasks: int
    team_streak: int
    leaderboard: list[GroupLeaderboardEntry]
    recent_rewards: list[GroupRewardRead]
