from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import (
    GroupActivity,
    GroupChallenge,
    GroupMember,
    ProductivityGroup,
)
from app.models.user import User
from app.schemas.group import GroupChallengeCreate, GroupChallengeRead
from app.services.group_activity_service import log_group_activity
from app.services.group_progress_service import add_group_xp_award
from app.services.group_task_service import require_membership


async def challenge_progress(challenge: GroupChallenge, db: AsyncSession) -> int:
    count = await db.scalar(
        select(func.count()).select_from(GroupActivity).where(
            GroupActivity.group_id == challenge.group_id,
            GroupActivity.kind == "task_completed",
            GroupActivity.created_at >= challenge.starts_at,
            GroupActivity.created_at <= challenge.ends_at,
        )
    )
    return int(count or 0)


async def complete_challenge(challenge: GroupChallenge, db: AsyncSession) -> None:
    if challenge.completed_at or await challenge_progress(challenge, db) < challenge.target:
        return
    challenge.completed_at = datetime.now(timezone.utc)
    memberships = list(
        await db.scalars(
            select(GroupMember).where(
                GroupMember.group_id == challenge.group_id,
                GroupMember.joined_at <= challenge.completed_at,
            )
        )
    )
    for membership in memberships:
        await add_group_xp_award(
            challenge.group_id,
            membership.user_id,
            f"group-challenge:{challenge.id}:user:{membership.user_id}",
            f"Challenge reward: {challenge.title}",
            challenge.reward_xp,
            challenge.completed_at,
            db,
        )
    group = await db.get(ProductivityGroup, challenge.group_id)
    await log_group_activity(
        challenge.group_id,
        group.leader_id,
        "challenge_completed",
        f"Completed the team challenge: {challenge.title}",
        db,
        source_key=f"group-challenge:{challenge.id}:completed",
        created_at=challenge.completed_at,
    )


async def sync_group_challenges(group_id: UUID, db: AsyncSession) -> None:
    challenges = list(
        await db.scalars(select(GroupChallenge).where(GroupChallenge.group_id == group_id))
    )
    for challenge in challenges:
        await complete_challenge(challenge, db)


async def challenge_read(
    challenge: GroupChallenge, viewer_id: UUID, db: AsyncSession
) -> GroupChallengeRead:
    membership = await require_membership(challenge.group_id, viewer_id, db)
    progress = await challenge_progress(challenge, db)
    now = datetime.now(timezone.utc)
    return GroupChallengeRead(
        id=challenge.id,
        group_id=challenge.group_id,
        title=challenge.title,
        description=challenge.description,
        target=challenge.target,
        progress=min(progress, challenge.target),
        reward_xp=challenge.reward_xp,
        starts_at=challenge.starts_at,
        ends_at=challenge.ends_at,
        completed_at=challenge.completed_at,
        completed=challenge.completed_at is not None,
        expired=challenge.completed_at is None and challenge.ends_at < now,
        can_manage=membership.role == "leader",
    )


async def list_group_challenges(
    group_id: UUID, viewer_id: UUID, db: AsyncSession
) -> list[GroupChallengeRead]:
    await require_membership(group_id, viewer_id, db)
    await sync_group_challenges(group_id, db)
    await db.commit()
    challenges = list(
        await db.scalars(
            select(GroupChallenge)
            .where(GroupChallenge.group_id == group_id)
            .order_by(GroupChallenge.ends_at.asc())
        )
    )
    return [await challenge_read(item, viewer_id, db) for item in challenges]


async def create_group_challenge(
    group_id: UUID, payload: GroupChallengeCreate, leader: User, db: AsyncSession
) -> GroupChallengeRead:
    group = await db.get(ProductivityGroup, group_id)
    if not group or group.leader_id != leader.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group leader access required.")
    now = datetime.now(timezone.utc)
    if payload.ends_at <= now:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Challenge deadline must be in the future.")
    challenge = GroupChallenge(
        group_id=group_id,
        created_by_id=leader.id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        target=payload.target,
        reward_xp=payload.reward_xp,
        starts_at=now,
        ends_at=payload.ends_at,
    )
    db.add(challenge)
    await db.flush()
    await log_group_activity(
        group_id,
        leader.id,
        "challenge_created",
        f"Started the team challenge: {challenge.title}",
        db,
        source_key=f"group-challenge:{challenge.id}:created",
        created_at=challenge.starts_at,
    )
    await db.commit()
    await db.refresh(challenge)
    return await challenge_read(challenge, leader.id, db)


async def delete_group_challenge(
    challenge_id: UUID, leader_id: UUID, db: AsyncSession
) -> None:
    challenge = await db.get(GroupChallenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")
    group = await db.get(ProductivityGroup, challenge.group_id)
    if not group or group.leader_id != leader_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group leader access required.")
    if challenge.completed_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed challenges cannot be deleted.")
    await log_group_activity(
        challenge.group_id,
        leader_id,
        "challenge_cancelled",
        f"Cancelled the team challenge: {challenge.title}",
        db,
        source_key=f"group-challenge:{challenge.id}:cancelled",
    )
    await db.delete(challenge)
    await db.commit()
