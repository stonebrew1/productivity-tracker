from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AchievementRead(BaseModel):
    id: UUID
    title: str
    description: str
    awarded_at: datetime
    task_id: UUID | None

    model_config = ConfigDict(from_attributes=True)
