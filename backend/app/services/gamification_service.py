from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import ActivityPost, XpAward
from app.models.task import Task, TaskVisibility
from app.services.stats_service import ensure_stats


TASK_COMPLETION_XP = 20
DAILY_XP_CAP = 200
XP_PER_LEVEL = 100


def level_from_xp(xp_total: int) -> int:
    return xp_total // XP_PER_LEVEL + 1


def gamification_snapshot(xp_total: int, current_streak: int) -> dict[str, int]:
    return {
        "xp_total": xp_total,
        "level": level_from_xp(xp_total),
        "xp_into_level": xp_total % XP_PER_LEVEL,
        "xp_for_next_level": XP_PER_LEVEL,
        "current_streak": current_streak,
    }


async def award_task_completion(task: Task, db: AsyncSession) -> int:
    existing = await db.scalar(select(XpAward).where(XpAward.task_id == task.id))
    if existing:
        return 0

    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    awarded_today = await db.scalar(
        select(func.coalesce(func.sum(XpAward.amount), 0)).where(
            XpAward.user_id == task.user_id,
            XpAward.awarded_at >= day_start,
            XpAward.awarded_at < day_end,
        )
    )
    amount = min(TASK_COMPLETION_XP, max(0, DAILY_XP_CAP - int(awarded_today or 0)))
    if amount:
        db.add(XpAward(task_id=task.id, user_id=task.user_id, amount=amount, awarded_at=now))
        stats = await ensure_stats(task.user_id, db)
        stats.xp_total += amount
    await db.flush()

    if task.visibility == TaskVisibility.PUBLIC:
        await ensure_activity_post(task, amount, db)
    return amount


async def ensure_activity_post(task: Task, xp_awarded: int, db: AsyncSession) -> ActivityPost:
    post = await db.scalar(select(ActivityPost).where(ActivityPost.task_id == task.id))
    if post:
        post.task_title = task.title
        post.xp_awarded = xp_awarded or post.xp_awarded
        return post
    post = ActivityPost(
        task_id=task.id,
        task_title=task.title,
        xp_awarded=xp_awarded,
        user_id=task.user_id,
        created_at=task.completed_at or datetime.now(timezone.utc),
    )
    db.add(post)
    await db.flush()
    return post


async def sync_activity_post(task: Task, db: AsyncSession) -> None:
    post = await db.scalar(select(ActivityPost).where(ActivityPost.task_id == task.id))
    if task.visibility == TaskVisibility.PRIVATE:
        if post:
            await db.delete(post)
        return
    if task.completed_at:
        award = await db.scalar(select(XpAward).where(XpAward.task_id == task.id))
        await ensure_activity_post(task, award.amount if award else 0, db)
