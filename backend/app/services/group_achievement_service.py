from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import (
    GroupAchievement,
    GroupActivity,
    GroupActivityReaction,
    GroupChallenge,
    GroupMember,
    GroupMilestone,
    GroupTask,
    ProductivityGroup,
)
from app.models.task import TaskStatus
from app.schemas.group import GroupAchievementRead
from app.services.group_activity_service import log_group_activity
from app.services.group_progress_service import add_group_xp_award, contribution_streak
from app.services.group_task_service import require_membership


@dataclass(frozen=True)
class AchievementDefinition:
    code: str
    title: str
    description: str
    rarity: str
    icon: str
    reward_xp: int
    target: int
    metric: str


GROUP_ACHIEVEMENTS = (
    AchievementDefinition(
        "first_finish",
        "First finish",
        "Complete the group's first shared task.",
        "common",
        "check",
        25,
        1,
        "completed_tasks",
    ),
    AchievementDefinition(
        "milestone_maker",
        "Milestone maker",
        "Reach two team milestones.",
        "rare",
        "flag",
        50,
        2,
        "completed_milestones",
    ),
    AchievementDefinition(
        "challenge_champion",
        "Challenge champion",
        "Complete a team challenge together.",
        "rare",
        "trophy",
        50,
        1,
        "completed_challenges",
    ),
    AchievementDefinition(
        "team_spirit",
        "Team spirit",
        "Give three recognition reactions across the group.",
        "rare",
        "heart",
        40,
        3,
        "recognitions",
    ),
    AchievementDefinition(
        "shared_momentum",
        "Shared momentum",
        "Maintain a three-day team completion streak.",
        "epic",
        "flame",
        60,
        3,
        "team_streak",
    ),
)


async def achievement_metrics(group_id: UUID, db: AsyncSession) -> dict[str, int]:
    completed_tasks = int(
        await db.scalar(
            select(func.count()).select_from(GroupTask).where(
                GroupTask.group_id == group_id,
                GroupTask.status == TaskStatus.DONE,
            )
        )
        or 0
    )
    completed_milestones = int(
        await db.scalar(
            select(func.count()).select_from(GroupMilestone).where(
                GroupMilestone.group_id == group_id,
                GroupMilestone.completed_at.is_not(None),
            )
        )
        or 0
    )
    completed_challenges = int(
        await db.scalar(
            select(func.count()).select_from(GroupChallenge).where(
                GroupChallenge.group_id == group_id,
                GroupChallenge.completed_at.is_not(None),
            )
        )
        or 0
    )
    recognitions = int(
        await db.scalar(
            select(func.count())
            .select_from(GroupActivityReaction)
            .join(GroupActivity, GroupActivity.id == GroupActivityReaction.activity_id)
            .where(GroupActivity.group_id == group_id)
        )
        or 0
    )
    completed_dates = list(
        await db.scalars(
            select(GroupTask.completed_at).where(
                GroupTask.group_id == group_id,
                GroupTask.status == TaskStatus.DONE,
                GroupTask.completed_at.is_not(None),
            )
        )
    )
    return {
        "completed_tasks": completed_tasks,
        "completed_milestones": completed_milestones,
        "completed_challenges": completed_challenges,
        "recognitions": recognitions,
        "team_streak": contribution_streak([value.date() for value in completed_dates]),
    }


async def evaluate_group_achievements(group_id: UUID, db: AsyncSession) -> None:
    group = await db.get(ProductivityGroup, group_id)
    if not group:
        return
    metrics = await achievement_metrics(group_id, db)
    unlocked_codes = set(
        await db.scalars(
            select(GroupAchievement.code).where(GroupAchievement.group_id == group_id)
        )
    )
    memberships = list(
        await db.scalars(select(GroupMember).where(GroupMember.group_id == group_id))
    )
    for definition in GROUP_ACHIEVEMENTS:
        if definition.code in unlocked_codes or metrics[definition.metric] < definition.target:
            continue
        unlocked_at = datetime.now(timezone.utc)
        achievement = GroupAchievement(
            group_id=group_id,
            code=definition.code,
            title=definition.title,
            description=definition.description,
            rarity=definition.rarity,
            icon=definition.icon,
            reward_xp=definition.reward_xp,
            unlocked_at=unlocked_at,
        )
        db.add(achievement)
        await db.flush()
        for membership in memberships:
            await add_group_xp_award(
                group_id,
                membership.user_id,
                f"group-achievement:{achievement.id}:user:{membership.user_id}",
                f"Group achievement: {definition.title}",
                definition.reward_xp,
                unlocked_at,
                db,
            )
        await log_group_activity(
            group_id,
            group.leader_id,
            "achievement_unlocked",
            f"Unlocked the group achievement: {definition.title}",
            db,
            source_key=f"group-achievement:{achievement.id}:unlocked",
            created_at=unlocked_at,
        )


async def list_group_achievements(
    group_id: UUID, viewer_id: UUID, db: AsyncSession
) -> list[GroupAchievementRead]:
    await require_membership(group_id, viewer_id, db)
    metrics = await achievement_metrics(group_id, db)
    unlocked = {
        item.code: item
        for item in list(
            await db.scalars(
                select(GroupAchievement).where(GroupAchievement.group_id == group_id)
            )
        )
    }
    return [
        GroupAchievementRead(
            code=definition.code,
            title=definition.title,
            description=definition.description,
            rarity=definition.rarity,
            icon=definition.icon,
            reward_xp=definition.reward_xp,
            progress=min(metrics[definition.metric], definition.target),
            target=definition.target,
            unlocked=definition.code in unlocked,
            unlocked_at=unlocked[definition.code].unlocked_at if definition.code in unlocked else None,
        )
        for definition in GROUP_ACHIEVEMENTS
    ]
