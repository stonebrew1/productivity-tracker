from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AchievementCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=2, max_length=500)
    task_id: UUID


class AchievementRead(BaseModel):
    id: UUID
    code: str | None
    title: str
    description: str
    category: str
    rarity: str
    icon: str
    awarded_at: datetime
    task_id: UUID | None

    model_config = ConfigDict(from_attributes=True)
