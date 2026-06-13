import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.group import GroupInvitation, GroupMember, ProductivityGroup
from app.models.social import Notification
from app.models.user import User
from app.models.user_stats import UserStats
from app.schemas.group import GroupInvitationRead, GroupMemberRead, GroupRead
from app.services.gamification_service import level_from_xp
from app.services.friendship_service import are_friends


async def group_read(group: ProductivityGroup, viewer_id: UUID, db: AsyncSession) -> GroupRead:
    membership = await db.scalar(
        select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == viewer_id)
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    rows = (
        await db.execute(
            select(GroupMember, User, UserStats)
            .join(User, User.id == GroupMember.user_id)
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .where(GroupMember.group_id == group.id)
            .order_by(GroupMember.role.asc(), GroupMember.joined_at.asc())
        )
    ).all()
    members = [
        GroupMemberRead(
            user_id=user.id,
            display_name=user.display_name,
            email=user.email,
            avatar_url=user.avatar_url,
            level=level_from_xp(stats.xp_total if stats else 0),
            role=member.role,
            joined_at=member.joined_at,
        )
        for member, user, stats in rows
    ]
    return GroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        role=membership.role,
        invite_code=group.invite_code if membership.role == "leader" else None,
        member_count=len(members),
        members=members,
    )


async def list_groups(user_id: UUID, db: AsyncSession) -> list[GroupRead]:
    groups = list(
        await db.scalars(
            select(ProductivityGroup)
            .join(GroupMember, GroupMember.group_id == ProductivityGroup.id)
            .where(GroupMember.user_id == user_id)
            .order_by(ProductivityGroup.created_at.asc())
        )
    )
    return [await group_read(group, user_id, db) for group in groups]


async def create_group(name: str, description: str | None, leader: User, db: AsyncSession) -> GroupRead:
    group = ProductivityGroup(
        name=name.strip(),
        description=description.strip() if description else None,
        invite_code=await unique_invite_code(db),
        leader_id=leader.id,
    )
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=leader.id, role="leader"))
    await db.commit()
    return await group_read(group, leader.id, db)


async def join_by_code(code: str, user: User, db: AsyncSession) -> GroupRead:
    group = await db.scalar(
        select(ProductivityGroup).where(ProductivityGroup.invite_code == code.strip().upper())
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code is invalid.")
    existing = await db.scalar(
        select(GroupMember).where(GroupMember.group_id == group.id, GroupMember.user_id == user.id)
    )
    if not existing:
        db.add(GroupMember(group_id=group.id, user_id=user.id))
        pending_invitation = await db.scalar(
            select(GroupInvitation).where(
                GroupInvitation.group_id == group.id,
                GroupInvitation.invited_user_id == user.id,
                GroupInvitation.status == "pending",
            )
        )
        if pending_invitation:
            pending_invitation.status = "accepted"
            pending_invitation.responded_at = datetime.now(timezone.utc)
        await db.commit()
    return await group_read(group, user.id, db)


async def invite_user(group_id: UUID, user_id: UUID, leader: User, db: AsyncSession) -> None:
    group = await require_leader(group_id, leader.id, db)
    if user_id == leader.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already lead this group.")
    if await db.scalar(
        select(GroupMember.id).where(GroupMember.group_id == group.id, GroupMember.user_id == user_id)
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This user is already a member.")
    target = await db.get(User, user_id)
    if not target or not await are_friends(leader.id, user_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Add this user as a friend before inviting them.")
    pending = await db.scalar(
        select(GroupInvitation).where(
            GroupInvitation.group_id == group.id,
            GroupInvitation.invited_user_id == user_id,
            GroupInvitation.status == "pending",
        )
    )
    if pending:
        return
    db.add(
        GroupInvitation(
            group_id=group.id,
            invited_user_id=user_id,
            invited_by_id=leader.id,
        )
    )
    db.add(
        Notification(
            kind="group",
            message=f"invited you to join {group.name}",
            recipient_id=user_id,
            actor_id=leader.id,
        )
    )
    await db.commit()


async def list_invitations(user_id: UUID, db: AsyncSession) -> list[GroupInvitationRead]:
    inviter = aliased(User)
    rows = (
        await db.execute(
            select(GroupInvitation, ProductivityGroup, inviter)
            .join(ProductivityGroup, ProductivityGroup.id == GroupInvitation.group_id)
            .join(inviter, inviter.id == GroupInvitation.invited_by_id)
            .where(
                GroupInvitation.invited_user_id == user_id,
                GroupInvitation.status == "pending",
            )
            .order_by(GroupInvitation.created_at.desc())
        )
    ).all()
    return [
        GroupInvitationRead(
            id=invitation.id,
            group_id=group.id,
            group_name=group.name,
            inviter_name=person.display_name or person.email.split("@")[0],
            status=invitation.status,
            created_at=invitation.created_at,
        )
        for invitation, group, person in rows
    ]


async def respond_invitation(invitation_id: UUID, user: User, accept: bool, db: AsyncSession) -> None:
    invitation = await db.get(GroupInvitation, invitation_id)
    if not invitation or invitation.invited_user_id != user.id or invitation.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    invitation.status = "accepted" if accept else "declined"
    invitation.responded_at = datetime.now(timezone.utc)
    if accept and not await db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == invitation.group_id,
            GroupMember.user_id == user.id,
        )
    ):
        db.add(GroupMember(group_id=invitation.group_id, user_id=user.id))
    await db.commit()


async def rotate_invite_code(group_id: UUID, leader_id: UUID, db: AsyncSession) -> GroupRead:
    group = await require_leader(group_id, leader_id, db)
    group.invite_code = await unique_invite_code(db)
    await db.commit()
    return await group_read(group, leader_id, db)


async def require_leader(group_id: UUID, user_id: UUID, db: AsyncSession) -> ProductivityGroup:
    group = await db.get(ProductivityGroup, group_id)
    if not group or group.leader_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group leader access required.")
    return group


async def unique_invite_code(db: AsyncSession) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not await db.scalar(
            select(ProductivityGroup.id).where(ProductivityGroup.invite_code == code)
        ):
            return code
