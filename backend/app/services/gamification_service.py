from datetime import datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.social import ActivityPost, GamificationRule, PostComment, PostReaction, QuestCompletion, XpAward
from app.models.task import Task, TaskStatus, TaskVisibility
from app.models.user_stats import UserStats
from app.schemas.gamification import BadgeProgressRead, GamificationDashboardRead, QuestRead
from app.schemas.social import GamificationRead
from app.services.achievement_service import BADGE_CATALOG, badge_metrics
from app.services.challenge_service import list_challenges
from app.services.stats_service import ensure_stats


DEFAULT_RULES = {
    "task_completion": {"xp": 20},
    "daily_xp_cap": {"xp": 200},
    "level_curve": {"xp_per_level": 100},
    "quest_rewards": {
        "daily_finish_2": 25,
        "daily_focus_1": 15,
        "weekly_finish_5": 60,
        "weekly_share_2": 30,
        "weekly_encourage_3": 25,
        "weekly_comment_2": 20,
    },
}

QUEST_CATALOG = [
    {
        "code": "daily_finish_2",
        "title": "Two solid wins",
        "description": "Complete two tasks today.",
        "cadence": "daily",
        "metric": "completed",
        "target": 2,
    },
    {
        "code": "daily_focus_1",
        "title": "Protect your focus",
        "description": "Complete one focus task today.",
        "cadence": "daily",
        "metric": "focus",
        "target": 1,
    },
    {
        "code": "weekly_finish_5",
        "title": "Weekly momentum",
        "description": "Complete five tasks this week.",
        "cadence": "weekly",
        "metric": "completed",
        "target": 5,
    },
    {
        "code": "weekly_share_2",
        "title": "Share the progress",
        "description": "Complete two public tasks this week.",
        "cadence": "weekly",
        "metric": "public",
        "target": 2,
    },
    {
        "code": "weekly_encourage_3",
        "title": "Lift the circle",
        "description": "Encourage three updates from friends this week.",
        "cadence": "weekly",
        "metric": "reactions",
        "target": 3,
    },
    {
        "code": "weekly_comment_2",
        "title": "Keep the conversation moving",
        "description": "Comment on two connection updates this week.",
        "cadence": "weekly",
        "metric": "comments",
        "target": 2,
    },
]


async def get_rules(db: AsyncSession) -> dict[str, dict]:
    rows = list(await db.scalars(select(GamificationRule).where(GamificationRule.is_active.is_(True))))
    by_code = {row.code: row.value for row in rows}
    for code, value in DEFAULT_RULES.items():
        if code not in by_code:
            db.add(GamificationRule(code=code, value=value))
            by_code[code] = value
    await db.flush()
    return by_code


def level_from_xp(xp_total: int, xp_per_level: int = 100) -> int:
    return xp_total // xp_per_level + 1


def gamification_snapshot(
    xp_total: int,
    current_streak: int,
    xp_per_level: int = 100,
) -> dict[str, int]:
    return {
        "xp_total": xp_total,
        "level": level_from_xp(xp_total, xp_per_level),
        "xp_into_level": xp_total % xp_per_level,
        "xp_for_next_level": xp_per_level,
        "current_streak": current_streak,
    }


async def award_task_completion(task: Task, db: AsyncSession) -> int:
    existing = await db.scalar(select(XpAward).where(XpAward.task_id == task.id))
    if existing:
        return 0

    rules = await get_rules(db)
    task_xp = int(rules["task_completion"]["xp"])
    daily_cap = int(rules["daily_xp_cap"]["xp"])
    now = datetime.now(timezone.utc)
    day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)
    awarded_today = await db.scalar(
        select(func.coalesce(func.sum(XpAward.amount), 0)).where(
            XpAward.user_id == task.user_id,
            XpAward.reason == "task_completed",
            XpAward.awarded_at >= day_start,
            XpAward.awarded_at < day_end,
        )
    )
    amount = min(task_xp, max(0, daily_cap - int(awarded_today or 0)))
    if amount:
        db.add(
            XpAward(
                task_id=task.id,
                source_key=f"task:{task.id}",
                user_id=task.user_id,
                amount=amount,
                awarded_at=now,
            )
        )
        stats = await ensure_stats(task.user_id, db)
        stats.xp_total += amount
    await db.flush()

    if task.visibility == TaskVisibility.PUBLIC:
        await ensure_activity_post(task, amount, db)
    return amount


async def award_quest_rewards(user_id: UUID, db: AsyncSession) -> int:
    rules = await get_rules(db)
    rewards = rules["quest_rewards"]
    total_awarded = 0
    for quest in QUEST_CATALOG:
        start, end = quest_period(quest["cadence"])
        progress = await quest_progress(user_id, quest["metric"], start, end, db)
        if progress < quest["target"]:
            continue
        existing = await db.scalar(
            select(QuestCompletion).where(
                QuestCompletion.user_id == user_id,
                QuestCompletion.quest_code == quest["code"],
                QuestCompletion.period_start == start,
            )
        )
        if existing:
            continue
        reward = int(rewards[quest["code"]])
        source_key = f"quest:{quest['code']}:{start.date().isoformat()}:{user_id}"
        db.add(
            QuestCompletion(
                quest_code=quest["code"],
                period_start=start,
                xp_awarded=reward,
                user_id=user_id,
            )
        )
        db.add(
            XpAward(
                source_key=source_key,
                user_id=user_id,
                amount=reward,
                reason="quest_completed",
            )
        )
        stats = await ensure_stats(user_id, db)
        stats.xp_total += reward
        total_awarded += reward
    await db.flush()
    return total_awarded


async def gamification_dashboard(user_id: UUID, db: AsyncSession) -> GamificationDashboardRead:
    rules = await get_rules(db)
    stats = await ensure_stats(user_id, db)
    xp_per_level = int(rules["level_curve"]["xp_per_level"])
    metrics = await badge_metrics(user_id, db)
    unlocked = {
        item.code: item
        for item in await db.scalars(
            select(Achievement).where(
                Achievement.user_id == user_id,
                Achievement.code.is_not(None),
            )
        )
    }
    badges = [
        BadgeProgressRead(
            code=badge["code"],
            title=badge["title"],
            description=badge["description"],
            category=badge["category"],
            rarity=badge["rarity"],
            icon=badge["icon"],
            progress=min(metrics[badge["metric"]], badge["target"]),
            target=badge["target"],
            unlocked=badge["code"] in unlocked,
            awarded_at=unlocked[badge["code"]].awarded_at if badge["code"] in unlocked else None,
        )
        for badge in BADGE_CATALOG
    ]
    quests = []
    rewards = rules["quest_rewards"]
    for quest in QUEST_CATALOG:
        start, end = quest_period(quest["cadence"])
        progress = await quest_progress(user_id, quest["metric"], start, end, db)
        completed = await db.scalar(
            select(QuestCompletion.id).where(
                QuestCompletion.user_id == user_id,
                QuestCompletion.quest_code == quest["code"],
                QuestCompletion.period_start == start,
            )
        )
        quests.append(
            QuestRead(
                code=quest["code"],
                title=quest["title"],
                description=quest["description"],
                cadence=quest["cadence"],
                progress=quest["target"] if completed else min(progress, quest["target"]),
                target=quest["target"],
                reward_xp=int(rewards[quest["code"]]),
                completed=bool(completed),
                expires_at=end,
            )
        )
    game = gamification_snapshot(stats.xp_total, stats.current_streak, xp_per_level)
    return GamificationDashboardRead(
        progression=GamificationRead(**game),
        badges=badges,
        quests=quests,
        showcased_badges=[badge for badge in badges if badge.unlocked][-3:],
        challenges=await list_challenges(user_id, db),
    )


def quest_period(cadence: str, now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or datetime.now(timezone.utc)
    day_start = datetime.combine(current.date(), time.min, tzinfo=timezone.utc)
    if cadence == "daily":
        return day_start, day_start + timedelta(days=1)
    week_start = day_start - timedelta(days=day_start.weekday())
    return week_start, week_start + timedelta(days=7)


async def quest_progress(
    user_id: UUID,
    metric: str,
    start: datetime,
    end: datetime,
    db: AsyncSession,
) -> int:
    if metric == "reactions":
        count = await db.scalar(
            select(func.count()).select_from(PostReaction).where(
                PostReaction.user_id == user_id,
                PostReaction.created_at >= start,
                PostReaction.created_at < end,
            )
        )
        return int(count or 0)
    if metric == "comments":
        count = await db.scalar(
            select(func.count())
            .select_from(PostComment)
            .join(ActivityPost, ActivityPost.id == PostComment.post_id)
            .where(
                PostComment.user_id == user_id,
                ActivityPost.user_id != user_id,
                PostComment.created_at >= start,
                PostComment.created_at < end,
            )
        )
        return int(count or 0)

    filters = [
        Task.user_id == user_id,
        Task.status == TaskStatus.DONE,
        Task.completed_at >= start,
        Task.completed_at < end,
    ]
    if metric == "focus":
        filters.append(Task.is_focus.is_(True))
    if metric == "public":
        filters.append(Task.visibility == TaskVisibility.PUBLIC)
    count = await db.scalar(select(func.count()).select_from(Task).where(*filters))
    return int(count or 0)


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
