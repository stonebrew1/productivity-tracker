from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Friendship


def friendship_pair(left_id: UUID, right_id: UUID):
    return or_(
        and_(Friendship.requester_id == left_id, Friendship.addressee_id == right_id),
        and_(Friendship.requester_id == right_id, Friendship.addressee_id == left_id),
    )


async def friendship_between(
    left_id: UUID, right_id: UUID, db: AsyncSession
) -> Friendship | None:
    return await db.scalar(select(Friendship).where(friendship_pair(left_id, right_id)))


async def are_friends(left_id: UUID, right_id: UUID, db: AsyncSession) -> bool:
    return bool(
        await db.scalar(
            select(Friendship.id).where(
                friendship_pair(left_id, right_id),
                Friendship.status == "accepted",
            )
        )
    )


def friend_ids_query(user_id: UUID):
    return (
        select(
            Friendship.addressee_id.label("friend_id")
        )
        .where(
            Friendship.requester_id == user_id,
            Friendship.status == "accepted",
        )
        .union_all(
            select(Friendship.requester_id.label("friend_id")).where(
                Friendship.addressee_id == user_id,
                Friendship.status == "accepted",
            )
        )
    )
