from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


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
    relationship_status: str
    relationship_id: UUID | None


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
    comments_count: int


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


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=280)


class CommentRead(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    author: FeedAuthor
    can_delete: bool


class NotificationRead(BaseModel):
    id: UUID
    kind: str
    message: str
    is_read: bool
    created_at: datetime
    post_id: UUID | None
    friendship_id: UUID | None
    friendship_status: str | None
    actor: FeedAuthor


class ChallengeRead(BaseModel):
    id: UUID
    code: str
    title: str
    description: str
    target: int
    reward_xp: int
    starts_at: datetime
    ends_at: datetime
    team_progress: int
    my_progress: int
    participant_count: int
    joined: bool
    completed: bool
    rewarded: bool


class CommitmentInvite(BaseModel):
    partner_id: UUID


class CommitmentRead(BaseModel):
    id: UUID
    task_id: UUID
    task_title: str
    task_status: str
    status: str
    bonus_xp: int
    created_at: datetime
    responded_at: datetime | None
    completed_at: datetime | None
    owner: FeedAuthor
    partner: FeedAuthor
    role: str
