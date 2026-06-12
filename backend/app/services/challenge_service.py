from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Challenge, ChallengeMember, Notification, XpAward
from app.models.task import Task, TaskStatus, TaskVisibility
from app.schemas.social import ChallengeRead
from app.services.stats_service import ensure_stats


async def list_challenges(user_id: UUID, db: AsyncSession) -> list[ChallengeRead]:
    now = datetime.now(timezone.utc)
    challenges = list(
        await db.scalars(
            select(Challenge)
            .where(Challenge.is_active.is_(True), Challenge.ends_at > now)
            .order_by(Challenge.ends_at.asc())
        )
    )
    return [await challenge_snapshot(challenge, user_id, db) for challenge in challenges]


async def challenge_snapshot(
    challenge: Challenge,
    user_id: UUID,
    db: AsyncSession,
) -> ChallengeRead:
    member_ids = list(
        await db.scalars(
            select(ChallengeMember.user_id).where(ChallengeMember.challenge_id == challenge.id)
        )
    )
    joined = user_id in member_ids
    team_progress = await team_contribution_count(challenge, db)
    my_progress = await member_contribution_count(challenge, user_id, db) if joined else 0
    rewarded = bool(
        await db.scalar(
            select(XpAward.id).where(
                XpAward.user_id == user_id,
                XpAward.source_key == challenge_reward_key(challenge.id, user_id),
            )
        )
    )
    return ChallengeRead(
        id=challenge.id,
        code=challenge.code,
        title=challenge.title,
        description=challenge.description,
        target=challenge.target,
        reward_xp=challenge.reward_xp,
        starts_at=challenge.starts_at,
        ends_at=challenge.ends_at,
        team_progress=min(team_progress, challenge.target),
        my_progress=my_progress,
        participant_count=len(member_ids),
        joined=joined,
        completed=team_progress >= challenge.target,
        rewarded=rewarded,
    )


async def team_contribution_count(
    challenge: Challenge,
    db: AsyncSession,
) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Task)
        .join(
            ChallengeMember,
            (ChallengeMember.user_id == Task.user_id)
            & (ChallengeMember.challenge_id == challenge.id),
        )
        .where(
            Task.status == TaskStatus.DONE,
            Task.visibility == TaskVisibility.PUBLIC,
            Task.completed_at >= challenge.starts_at,
            Task.completed_at >= ChallengeMember.joined_at,
            Task.completed_at < challenge.ends_at,
        )
    )
    return int(count or 0)


async def member_contribution_count(
    challenge: Challenge,
    user_id: UUID,
    db: AsyncSession,
) -> int:
    membership = await db.scalar(
        select(ChallengeMember).where(
            ChallengeMember.challenge_id == challenge.id,
            ChallengeMember.user_id == user_id,
        )
    )
    if not membership:
        return 0
    count = await db.scalar(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.DONE,
            Task.visibility == TaskVisibility.PUBLIC,
            Task.completed_at >= challenge.starts_at,
            Task.completed_at >= membership.joined_at,
            Task.completed_at < challenge.ends_at,
        )
    )
    return int(count or 0)


async def award_challenge_rewards(task: Task, db: AsyncSession) -> int:
    if task.visibility != TaskVisibility.PUBLIC or not task.completed_at:
        return 0
    challenges = list(
        await db.scalars(
            select(Challenge)
            .join(ChallengeMember, ChallengeMember.challenge_id == Challenge.id)
            .where(
                ChallengeMember.user_id == task.user_id,
                Challenge.is_active.is_(True),
                Challenge.starts_at <= task.completed_at,
                Challenge.ends_at > task.completed_at,
            )
        )
    )
    total_awarded = 0
    for challenge in challenges:
        member_ids = list(
            await db.scalars(
                select(ChallengeMember.user_id).where(ChallengeMember.challenge_id == challenge.id)
            )
        )
        if await team_contribution_count(challenge, db) < challenge.target:
            continue
        for member_id in member_ids:
            source_key = challenge_reward_key(challenge.id, member_id)
            if await db.scalar(select(XpAward.id).where(XpAward.source_key == source_key)):
                continue
            db.add(
                XpAward(
                    source_key=source_key,
                    user_id=member_id,
                    amount=challenge.reward_xp,
                    reason="challenge_completed",
                )
            )
            stats = await ensure_stats(member_id, db)
            stats.xp_total += challenge.reward_xp
            total_awarded += challenge.reward_xp
            if member_id != task.user_id:
                db.add(
                    Notification(
                        kind="challenge",
                        message=f"completed the team challenge {challenge.title}",
                        recipient_id=member_id,
                        actor_id=task.user_id,
                    )
                )
    await db.flush()
    return total_awarded


def challenge_reward_key(challenge_id: UUID, user_id: UUID) -> str:
    return f"challenge:{challenge_id}:{user_id}"
