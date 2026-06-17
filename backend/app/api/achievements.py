from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.achievement import Achievement
from app.models.task import Task
from app.models.user import User
from app.schemas.achievement import AchievementCreate, AchievementRead


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


@router.post("", response_model=AchievementRead, status_code=201)
async def create_achievement(
    payload: AchievementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Achievement:
    task = await db.get(Task, payload.task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task.")
    achievement = Achievement(
        title=payload.title.strip(),
        description=payload.description.strip(),
        category="personal",
        rarity="common",
        icon="medal",
        user_id=current_user.id,
        task_id=task.id,
    )
    db.add(achievement)
    await db.commit()
    await db.refresh(achievement)
    return achievement
