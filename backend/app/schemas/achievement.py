from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
