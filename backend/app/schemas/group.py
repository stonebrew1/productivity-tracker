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


class GroupActivityCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class GroupActivityAuthor(BaseModel):
    id: UUID
    display_name: str
    avatar_url: str | None


class GroupActivityCommentRead(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    author: GroupActivityAuthor
    can_delete: bool


class GroupActivityRead(BaseModel):
    id: UUID
    kind: str
    content: str
    created_at: datetime
    author: GroupActivityAuthor
    comments: list[GroupActivityCommentRead]
    reactions_count: int
    reacted_by_me: bool
    can_react: bool


class GroupVelocityPoint(BaseModel):
    date: datetime
    completed: int


class GroupWorkloadEntry(BaseModel):
    user_id: UUID
    display_name: str
    active_tasks: int
    completed_tasks: int
    overdue_tasks: int


class GroupMilestoneRisk(BaseModel):
    milestone_id: UUID
    title: str
    progress_percent: int
    target_date: datetime | None
    risk: str


class GroupAnalyticsRead(BaseModel):
    total_tasks: int
    completion_rate: int
    active_tasks: int
    overdue_tasks: int
    due_soon_tasks: int
    average_cycle_days: float
    workload_balance_score: int
    velocity: list[GroupVelocityPoint]
    workload: list[GroupWorkloadEntry]
    milestone_risks: list[GroupMilestoneRisk]


class GroupChallengeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=500)
    target: int = Field(ge=1, le=100)
    reward_xp: int = Field(ge=10, le=500)
    ends_at: datetime


class GroupChallengeRead(BaseModel):
    id: UUID
    group_id: UUID
    title: str
    description: str | None
    target: int
    progress: int
    reward_xp: int
    starts_at: datetime
    ends_at: datetime
    completed_at: datetime | None
    completed: bool
    expired: bool
    can_manage: bool
