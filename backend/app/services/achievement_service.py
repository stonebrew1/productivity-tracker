from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.task import Task, TaskStatus


async def check_and_award(user_id: UUID, task: Task, db: AsyncSession) -> list[Achievement]:
    completed_count = await db.scalar(
        select(func.count()).select_from(Task).where(Task.user_id == user_id, Task.status == TaskStatus.DONE)
    )
    new_achievements: list[Achievement] = []

    if completed_count == 1:
        new_achievements.append(
            Achievement(
                title="First win",
                description="Completed the first task.",
                user_id=user_id,
                task_id=task.id,
            )
        )

    if task.deadline and task.completed_at and task.completed_at <= task.deadline:
        new_achievements.append(
            Achievement(
                title="On time",
                description="Completed a task before its deadline.",
                user_id=user_id,
                task_id=task.id,
            )
        )

    if completed_count and completed_count % 5 == 0:
        new_achievements.append(
            Achievement(
                title=f"{completed_count} tasks completed",
                description="Reached a productivity milestone.",
                user_id=user_id,
                task_id=task.id,
            )
        )

    for achievement in new_achievements:
        achievement.awarded_at = datetime.now(timezone.utc)
        db.add(achievement)

    await db.flush()
    return new_achievements
