from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class GamificationRead(BaseModel):
    xp_total: int
    level: int
    xp_into_level: int
    xp_for_next_level: int
    current_streak: int


class ProfileRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    gamification: GamificationRead


class PersonRead(BaseModel):
    id: UUID
    display_name: str | None
    email: EmailStr
    avatar_url: str | None
    level: int
    current_streak: int
    last_active_at: datetime | None
    is_following: bool


class FeedAuthor(BaseModel):
    id: UUID
    display_name: str | None
    email: EmailStr
    avatar_url: str | None
    level: int


class FeedPostRead(BaseModel):
    id: UUID
    task_title: str
    xp_awarded: int
    created_at: datetime
    author: FeedAuthor
    reactions_count: int
    reacted_by_me: bool


class LeaderboardEntryRead(BaseModel):
    rank: int
    user_id: UUID
    display_name: str | None
    email: EmailStr
    avatar_url: str | None
    level: int
    current_streak: int
    weekly_xp: int
    is_current_user: bool
