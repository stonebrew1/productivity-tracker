from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.achievement import Achievement
from app.models.user import User
from app.schemas.achievement import AchievementRead


router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("", response_model=list[AchievementRead])
async def list_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Achievement]:
    result = await db.scalars(
        select(Achievement).where(Achievement.user_id == current_user.id).order_by(Achievement.awarded_at.desc())
    )
    return list(result)
