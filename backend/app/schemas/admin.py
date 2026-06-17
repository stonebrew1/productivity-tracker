from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.user import UserRole


class AdminUserRead(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    role: UserRole
    is_email_verified: bool
    is_blocked: bool
    blocked_at: datetime | None
    created_at: datetime
    total_tasks: int
    completed_tasks: int


class AdminUserPage(BaseModel):
    items: list[AdminUserRead]
    total: int
    limit: int
    offset: int


class AdminSummary(BaseModel):
    total_users: int
    verified_users: int
    blocked_users: int
    administrators: int
    total_tasks: int
    completed_tasks: int
    total_achievements: int
    total_groups: int
    completion_rate: float
    tasks_by_status: dict[str, int]
