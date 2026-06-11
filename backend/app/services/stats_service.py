from uuid import UUID

from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.user_stats import UserStats


async def ensure_stats(user_id: UUID, db: AsyncSession) -> UserStats:
    stats = await db.scalar(select(UserStats).where(UserStats.user_id == user_id))
    if stats:
        return stats
    stats = UserStats(user_id=user_id)
    db.add(stats)
    await db.flush()
    return stats


async def recalculate_stats(user_id: UUID, db: AsyncSession) -> UserStats:
    stats = await ensure_stats(user_id, db)
    total_tasks = await db.scalar(select(func.count()).select_from(Task).where(Task.user_id == user_id))
    completed_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(Task.user_id == user_id, Task.status == TaskStatus.DONE)
    )
    stats.total_tasks = total_tasks or 0
    stats.completed_tasks = completed_tasks or 0
    completion_dates = list(
        await db.scalars(
            select(cast(Task.completed_at, Date))
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.DONE,
                Task.completed_at.is_not(None),
            )
            .distinct()
            .order_by(cast(Task.completed_at, Date).desc())
        )
    )
    stats.current_streak = calculate_current_streak(completion_dates)
    await db.flush()
    return stats


def calculate_current_streak(completion_dates: list[date], today: date | None = None) -> int:
    if not completion_dates:
        return 0
    current_day = today or date.today()
    unique_dates = sorted(set(completion_dates), reverse=True)
    if unique_dates[0] < current_day - timedelta(days=1):
        return 0

    streak = 1
    expected = unique_dates[0] - timedelta(days=1)
    for completed_on in unique_dates[1:]:
        if completed_on != expected:
            break
        streak += 1
        expected -= timedelta(days=1)
    return streak
