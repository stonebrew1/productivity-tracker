from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.task import Task, TaskStatus, TaskVisibility
from app.models.user_stats import UserStats


BADGE_CATALOG = [
    {
        "code": "first_win",
        "title": "First win",
        "description": "Complete your first task.",
        "category": "completion",
        "rarity": "common",
        "icon": "check",
        "metric": "completed",
        "target": 1,
    },
    {
        "code": "momentum_5",
        "title": "Momentum",
        "description": "Complete five tasks.",
        "category": "completion",
        "rarity": "common",
        "icon": "zap",
        "metric": "completed",
        "target": 5,
    },
    {
        "code": "deep_focus_3",
        "title": "Deep focus",
        "description": "Complete three focus tasks.",
        "category": "focus",
        "rarity": "rare",
        "icon": "target",
        "metric": "focus",
        "target": 3,
    },
    {
        "code": "deadline_keeper_5",
        "title": "Deadline keeper",
        "description": "Finish five tasks on or before their deadline.",
        "category": "planning",
        "rarity": "rare",
        "icon": "clock",
        "metric": "on_time",
        "target": 5,
    },
    {
        "code": "open_book_3",
        "title": "Open book",
        "description": "Share three completed tasks with friends.",
        "category": "social",
        "rarity": "rare",
        "icon": "globe",
        "metric": "public",
        "target": 3,
    },
    {
        "code": "streak_3",
        "title": "Three-day rhythm",
        "description": "Maintain a three-day completion streak.",
        "category": "consistency",
        "rarity": "epic",
        "icon": "flame",
        "metric": "streak",
        "target": 3,
    },
    {
        "code": "century",
        "title": "Century",
        "description": "Complete one hundred tasks.",
        "category": "completion",
        "rarity": "legendary",
        "icon": "trophy",
        "metric": "completed",
        "target": 100,
    },
]


async def badge_metrics(user_id: UUID, db: AsyncSession) -> dict[str, int]:
    stats = await db.scalar(select(UserStats).where(UserStats.user_id == user_id))
    completed = await db.scalar(
        select(func.count()).select_from(Task).where(Task.user_id == user_id, Task.status == TaskStatus.DONE)
    )
    focus = await db.scalar(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.status == TaskStatus.DONE, Task.is_focus.is_(True)
        )
    )
    on_time = await db.scalar(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.DONE,
            Task.deadline.is_not(None),
            Task.completed_at <= Task.deadline,
        )
    )
    public = await db.scalar(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.DONE,
            Task.visibility == TaskVisibility.PUBLIC,
        )
    )
    return {
        "completed": int(completed or 0),
        "focus": int(focus or 0),
        "on_time": int(on_time or 0),
        "public": int(public or 0),
        "streak": stats.current_streak if stats else 0,
    }


async def check_and_award(user_id: UUID, task: Task, db: AsyncSession) -> list[Achievement]:
    metrics = await badge_metrics(user_id, db)
    existing_codes = set(
        await db.scalars(
            select(Achievement.code).where(
                Achievement.user_id == user_id,
                Achievement.code.is_not(None),
            )
        )
    )
    awarded: list[Achievement] = []
    for badge in BADGE_CATALOG:
        if badge["code"] in existing_codes:
            continue
        if metrics[badge["metric"]] < badge["target"]:
            continue
        achievement = Achievement(
            code=badge["code"],
            title=badge["title"],
            description=badge["description"],
            category=badge["category"],
            rarity=badge["rarity"],
            icon=badge["icon"],
            awarded_at=datetime.now(timezone.utc),
            user_id=user_id,
            task_id=task.id,
        )
        db.add(achievement)
        awarded.append(achievement)
    await db.flush()
    return awarded
