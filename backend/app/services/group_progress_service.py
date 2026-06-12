from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember, GroupMilestone, GroupTask, GroupXpAward
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.group import (
    GroupLeaderboardEntry,
    GroupProgressRead,
    GroupRewardRead,
)
from app.services.group_task_service import require_membership

TASK_COMPLETION_XP = 25
MILESTONE_COMPLETION_XP = 50


def contribution_streak(completed_dates: list[date], today: date | None = None) -> int:
    unique_dates = sorted(set(completed_dates), reverse=True)
    if not unique_dates:
        return 0
    current = today or datetime.now(timezone.utc).date()
    if unique_dates[0] not in {current, current - timedelta(days=1)}:
        return 0
    streak = 0
    expected = unique_dates[0]
    for completed_on in unique_dates:
        if completed_on != expected:
            break
        streak += 1
        expected -= timedelta(days=1)
    return streak


async def _add_award(
    group_id: UUID,
    user_id: UUID,
    source_key: str,
    reason: str,
    amount: int,
    awarded_at: datetime | None,
    db: AsyncSession,
) -> bool:
    existing = await db.scalar(select(GroupXpAward).where(GroupXpAward.source_key == source_key))
    if existing:
        existing.user_id = user_id
        existing.reason = reason
        existing.amount = amount
        return False
    db.add(
        GroupXpAward(
            group_id=group_id,
            user_id=user_id,
            source_key=source_key,
            reason=reason,
            amount=amount,
            awarded_at=awarded_at or datetime.now(timezone.utc),
        )
    )
    return True


async def award_task_completion(task: GroupTask, db: AsyncSession) -> None:
    if task.status != TaskStatus.DONE:
        return
    await _add_award(
        task.group_id,
        task.assigned_to_id,
        f"group-task:{task.id}",
        f"Completed {task.title}",
        TASK_COMPLETION_XP,
        task.completed_at,
        db,
    )
    if task.milestone_id:
        await award_milestone_completion(task.milestone_id, db)


async def award_milestone_completion(milestone_id: UUID, db: AsyncSession) -> None:
    milestone = await db.get(GroupMilestone, milestone_id)
    if not milestone:
        return
    task_count = await db.scalar(
        select(func.count()).select_from(GroupTask).where(GroupTask.milestone_id == milestone_id)
    ) or 0
    completed_count = await db.scalar(
        select(func.count()).select_from(GroupTask).where(
            GroupTask.milestone_id == milestone_id,
            GroupTask.status == TaskStatus.DONE,
        )
    ) or 0
    if not task_count or completed_count != task_count:
        return
    if not milestone.completed_at:
        milestone.completed_at = datetime.now(timezone.utc)
    memberships = list(
        await db.scalars(
            select(GroupMember).where(
                GroupMember.group_id == milestone.group_id,
                GroupMember.joined_at <= milestone.completed_at,
            )
        )
    )
    for membership in memberships:
        await _add_award(
            milestone.group_id,
            membership.user_id,
            f"group-milestone:{milestone.id}:user:{membership.user_id}",
            f"Milestone reached: {milestone.title}",
            MILESTONE_COMPLETION_XP,
            milestone.completed_at,
            db,
        )


async def sync_group_rewards(group_id: UUID, db: AsyncSession) -> None:
    tasks = list(
        await db.scalars(
            select(GroupTask).where(
                GroupTask.group_id == group_id,
                GroupTask.status == TaskStatus.DONE,
            )
        )
    )
    for task in tasks:
        await award_task_completion(task, db)
    milestones = list(
        await db.scalars(select(GroupMilestone.id).where(GroupMilestone.group_id == group_id))
    )
    for milestone_id in milestones:
        await award_milestone_completion(milestone_id, db)


async def group_progress(
    group_id: UUID, viewer_id: UUID, db: AsyncSession
) -> GroupProgressRead:
    await require_membership(group_id, viewer_id, db)
    await sync_group_rewards(group_id, db)
    await db.commit()

    memberships = list(
        await db.scalars(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at.asc())
        )
    )
    users = {
        user.id: user
        for user in list(
            await db.scalars(select(User).where(User.id.in_([item.user_id for item in memberships])))
        )
    }
    tasks = list(
        await db.scalars(
            select(GroupTask).where(
                GroupTask.group_id == group_id,
                GroupTask.status == TaskStatus.DONE,
                GroupTask.completed_at.is_not(None),
            )
        )
    )
    awards = list(
        await db.scalars(
            select(GroupXpAward)
            .where(GroupXpAward.group_id == group_id)
            .order_by(GroupXpAward.awarded_at.desc())
        )
    )
    xp_by_user: dict[UUID, int] = defaultdict(int)
    dates_by_user: dict[UUID, list[date]] = defaultdict(list)
    completed_by_user: dict[UUID, int] = defaultdict(int)
    for award in awards:
        xp_by_user[award.user_id] += award.amount
    for task in tasks:
        completed_by_user[task.assigned_to_id] += 1
        dates_by_user[task.assigned_to_id].append(task.completed_at.date())

    ranked = sorted(
        memberships,
        key=lambda item: (
            -xp_by_user[item.user_id],
            -completed_by_user[item.user_id],
            item.joined_at,
        ),
    )
    leaderboard = []
    for rank, membership in enumerate(ranked, start=1):
        user = users[membership.user_id]
        leaderboard.append(
            GroupLeaderboardEntry(
                rank=rank,
                user_id=user.id,
                display_name=user.display_name or user.email.split("@")[0],
                avatar_url=user.avatar_url,
                group_xp=xp_by_user[user.id],
                completed_tasks=completed_by_user[user.id],
                contribution_streak=contribution_streak(dates_by_user[user.id]),
                is_current_user=user.id == viewer_id,
            )
        )
    team_dates = [task.completed_at.date() for task in tasks]
    recent_rewards = []
    for award in awards[:5]:
        user = users.get(award.user_id)
        recent_rewards.append(
            GroupRewardRead(
                id=award.id,
                user_id=award.user_id,
                display_name=(user.display_name or user.email.split("@")[0]) if user else "Former member",
                reason=award.reason,
                amount=award.amount,
                awarded_at=award.awarded_at,
            )
        )
    return GroupProgressRead(
        total_group_xp=sum(item.amount for item in awards),
        completed_tasks=len(tasks),
        team_streak=contribution_streak(team_dates),
        leaderboard=leaderboard,
        recent_rewards=recent_rewards,
    )
