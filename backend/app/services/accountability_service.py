from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import AccountabilityCommitment, Follow, Notification, XpAward
from app.models.task import Task, TaskStatus, TaskVisibility
from app.models.user import User
from app.models.user_stats import UserStats
from app.schemas.social import CommitmentRead, FeedAuthor
from app.services.gamification_service import level_from_xp
from app.services.stats_service import ensure_stats


async def list_commitments(user_id: UUID, db: AsyncSession) -> list[CommitmentRead]:
    # Explicit aliases keep owner and partner profile data unambiguous.
    from sqlalchemy.orm import aliased

    owner = aliased(User)
    partner = aliased(User)
    owner_stats = aliased(UserStats)
    partner_stats = aliased(UserStats)
    result = (
        await db.execute(
            select(
                AccountabilityCommitment,
                Task,
                owner,
                owner_stats,
                partner,
                partner_stats,
            )
            .join(Task, Task.id == AccountabilityCommitment.task_id)
            .join(owner, owner.id == AccountabilityCommitment.owner_id)
            .outerjoin(owner_stats, owner_stats.user_id == owner.id)
            .join(partner, partner.id == AccountabilityCommitment.partner_id)
            .outerjoin(partner_stats, partner_stats.user_id == partner.id)
            .where(
                or_(
                    AccountabilityCommitment.owner_id == user_id,
                    AccountabilityCommitment.partner_id == user_id,
                )
            )
            .order_by(AccountabilityCommitment.created_at.desc())
        )
    ).all()
    return [
        commitment_read(commitment, task, owner_user, owner_game, partner_user, partner_game, user_id)
        for commitment, task, owner_user, owner_game, partner_user, partner_game in result
    ]


async def invite_partner(
    task_id: UUID,
    partner_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> CommitmentRead:
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.status == TaskStatus.DONE or task.visibility != TaskVisibility.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accountability requires an unfinished public task.",
        )
    if partner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose another person.")
    partner = await db.get(User, partner_id)
    follows = await db.scalar(
        select(Follow.id).where(
            Follow.follower_id == current_user.id,
            Follow.followed_id == partner_id,
        )
    )
    if not partner or not follows:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow this person first.")
    if await db.scalar(select(AccountabilityCommitment.id).where(AccountabilityCommitment.task_id == task.id)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This task already has a partner.")
    commitment = AccountabilityCommitment(
        task_id=task.id,
        owner_id=current_user.id,
        partner_id=partner.id,
    )
    db.add(commitment)
    db.add(
        Notification(
            kind="accountability",
            message=f"invited you to support {task.title}",
            recipient_id=partner.id,
            actor_id=current_user.id,
        )
    )
    await db.commit()
    return await get_commitment(commitment.id, current_user.id, db)


async def respond_to_commitment(
    commitment_id: UUID,
    user_id: UUID,
    accept: bool,
    db: AsyncSession,
) -> CommitmentRead:
    commitment = await db.get(AccountabilityCommitment, commitment_id)
    if not commitment or commitment.partner_id != user_id or commitment.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending invitation not found.")
    commitment.status = "accepted" if accept else "declined"
    commitment.responded_at = datetime.now(timezone.utc)
    task = await db.get(Task, commitment.task_id)
    db.add(
        Notification(
            kind="accountability",
            message=f"{'accepted' if accept else 'declined'} your support request for {task.title}",
            recipient_id=commitment.owner_id,
            actor_id=user_id,
        )
    )
    await db.commit()
    return await get_commitment(commitment.id, user_id, db)


async def cancel_commitment(commitment_id: UUID, user_id: UUID, db: AsyncSession) -> None:
    commitment = await db.get(AccountabilityCommitment, commitment_id)
    if not commitment or user_id not in {commitment.owner_id, commitment.partner_id}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found.")
    if commitment.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed commitments cannot be cancelled.")
    await db.delete(commitment)
    await db.commit()


async def award_accountability_bonus(task: Task, db: AsyncSession) -> int:
    commitment = await db.scalar(
        select(AccountabilityCommitment).where(
            AccountabilityCommitment.task_id == task.id,
            AccountabilityCommitment.status == "accepted",
        )
    )
    if not commitment:
        return 0
    commitment.status = "completed"
    commitment.completed_at = task.completed_at or datetime.now(timezone.utc)
    total = 0
    for user_id, role in ((commitment.owner_id, "owner"), (commitment.partner_id, "partner")):
        source_key = accountability_reward_key(commitment.id, role)
        if await db.scalar(select(XpAward.id).where(XpAward.source_key == source_key)):
            continue
        db.add(
            XpAward(
                source_key=source_key,
                user_id=user_id,
                amount=commitment.bonus_xp,
                reason="accountability_completed",
            )
        )
        stats = await ensure_stats(user_id, db)
        stats.xp_total += commitment.bonus_xp
        total += commitment.bonus_xp
    db.add(
        Notification(
            kind="accountability",
            message=f"completed your accountability task {task.title}",
            recipient_id=commitment.partner_id,
            actor_id=commitment.owner_id,
        )
    )
    await db.flush()
    return total


async def get_commitment(
    commitment_id: UUID,
    viewer_id: UUID,
    db: AsyncSession,
) -> CommitmentRead:
    commitments = await list_commitments(viewer_id, db)
    for item in commitments:
        if item.id == commitment_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found.")


def commitment_read(
    commitment: AccountabilityCommitment,
    task: Task,
    owner: User,
    owner_stats: UserStats | None,
    partner: User,
    partner_stats: UserStats | None,
    viewer_id: UUID,
) -> CommitmentRead:
    return CommitmentRead(
        id=commitment.id,
        task_id=task.id,
        task_title=task.title,
        task_status=task.status.value,
        status=commitment.status,
        bonus_xp=commitment.bonus_xp,
        created_at=commitment.created_at,
        responded_at=commitment.responded_at,
        completed_at=commitment.completed_at,
        owner=author(owner, owner_stats),
        partner=author(partner, partner_stats),
        role="owner" if commitment.owner_id == viewer_id else "partner",
    )


def author(user: User, stats: UserStats | None) -> FeedAuthor:
    return FeedAuthor(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        avatar_url=user.avatar_url,
        level=level_from_xp(stats.xp_total if stats else 0),
    )


def accountability_reward_key(commitment_id: UUID, role: str) -> str:
    return f"accountability:{commitment_id}:{role}"
