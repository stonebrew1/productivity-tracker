from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
