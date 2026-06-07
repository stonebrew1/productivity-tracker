from uuid import UUID

from sqlalchemy import func, select
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
    stats.current_streak = stats.completed_tasks
    await db.flush()
    return stats
