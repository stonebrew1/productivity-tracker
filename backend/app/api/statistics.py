from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.stats import StatsRead
from app.services.stats_service import recalculate_stats


router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatsRead)
async def read_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsRead:
    stats = await recalculate_stats(current_user.id, db)
    by_priority_rows = await db.execute(
        select(Task.priority, func.count()).where(Task.user_id == current_user.id).group_by(Task.priority)
    )
    by_status_rows = await db.execute(
        select(Task.status, func.count()).where(Task.user_id == current_user.id).group_by(Task.status)
    )
    total = stats.total_tasks
    completed = stats.completed_tasks
    return StatsRead(
        total_tasks=total,
        completed_tasks=completed,
        current_streak=stats.current_streak,
        completion_rate=round((completed / total) * 100, 2) if total else 0,
        by_priority={priority.value: count for priority, count in by_priority_rows.all()},
        by_status={status.value: count for status, count in by_status_rows.all()},
    )
