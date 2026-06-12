from datetime import datetime

from pydantic import BaseModel

from app.schemas.social import ChallengeRead, GamificationRead


class BadgeProgressRead(BaseModel):
    code: str
    title: str
    description: str
    category: str
    rarity: str
    icon: str
    progress: int
    target: int
    unlocked: bool
    awarded_at: datetime | None


class QuestRead(BaseModel):
    code: str
    title: str
    description: str
    cadence: str
    progress: int
    target: int
    reward_xp: int
    completed: bool
    expires_at: datetime


class GamificationDashboardRead(BaseModel):
    progression: GamificationRead
    badges: list[BadgeProgressRead]
    quests: list[QuestRead]
    showcased_badges: list[BadgeProgressRead]
    challenges: list[ChallengeRead]
