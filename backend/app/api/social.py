from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.social import ActivityPost, Follow, PostReaction
from app.models.user import User
from app.models.user_stats import UserStats
from app.schemas.social import FeedAuthor, FeedPostRead, PersonRead, ProfileRead
from app.schemas.user import ProfileUpdate
from app.services.gamification_service import gamification_snapshot, level_from_xp
from app.services.stats_service import ensure_stats


router = APIRouter(prefix="/social", tags=["social"])


@router.get("/profile", response_model=ProfileRead)
async def read_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    stats = await ensure_stats(current_user.id, db)
    return profile_response(current_user, stats)


@router.put("/profile", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value.strip() if isinstance(value, str) else value)
    stats = await ensure_stats(current_user.id, db)
    await db.commit()
    return profile_response(current_user, stats)


@router.get("/people", response_model=list[PersonRead])
async def list_people(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PersonRead]:
    following_ids = set(
        await db.scalars(select(Follow.followed_id).where(Follow.follower_id == current_user.id))
    )
    rows = (
        await db.execute(
            select(User, UserStats)
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .where(User.id != current_user.id)
            .order_by(User.display_name.asc().nulls_last(), User.email)
            .limit(50)
        )
    ).all()
    return [
        PersonRead(
            id=user.id,
            display_name=user.display_name,
            email=user.email,
            avatar_url=user.avatar_url,
            level=level_from_xp(stats.xp_total if stats else 0),
            is_following=user.id in following_ids,
        )
        for user, stats in rows
    ]


@router.post("/people/{user_id}/follow", status_code=204)
async def follow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot follow yourself.")
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    existing = await db.scalar(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    )
    if not existing:
        db.add(Follow(follower_id=current_user.id, followed_id=user_id))
        await db.commit()


@router.delete("/people/{user_id}/follow", status_code=204)
async def unfollow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    follow = await db.scalar(
        select(Follow).where(Follow.follower_id == current_user.id, Follow.followed_id == user_id)
    )
    if follow:
        await db.delete(follow)
        await db.commit()


@router.get("/feed", response_model=list[FeedPostRead])
async def read_feed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeedPostRead]:
    followed = select(Follow.followed_id).where(Follow.follower_id == current_user.id)
    rows = (
        await db.execute(
            select(ActivityPost, User, UserStats)
            .join(User, User.id == ActivityPost.user_id)
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .where(or_(ActivityPost.user_id == current_user.id, ActivityPost.user_id.in_(followed)))
            .order_by(ActivityPost.created_at.desc())
            .limit(50)
        )
    ).all()
    post_ids = [post.id for post, _, _ in rows]
    reaction_counts: dict[UUID, int] = {}
    reacted_ids: set[UUID] = set()
    if post_ids:
        reaction_counts = dict(
            (
                await db.execute(
                    select(PostReaction.post_id, func.count())
                    .where(PostReaction.post_id.in_(post_ids))
                    .group_by(PostReaction.post_id)
                )
            ).all()
        )
        reacted_ids = set(
            await db.scalars(
                select(PostReaction.post_id).where(
                    PostReaction.post_id.in_(post_ids), PostReaction.user_id == current_user.id
                )
            )
        )
    return [
        FeedPostRead(
            id=post.id,
            task_title=post.task_title,
            xp_awarded=post.xp_awarded,
            created_at=post.created_at,
            author=FeedAuthor(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                avatar_url=user.avatar_url,
                level=level_from_xp(stats.xp_total if stats else 0),
            ),
            reactions_count=reaction_counts.get(post.id, 0),
            reacted_by_me=post.id in reacted_ids,
        )
        for post, user, stats in rows
    ]


@router.post("/posts/{post_id}/reaction", status_code=204)
async def add_reaction(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    post = await db.get(ActivityPost, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    allowed = post.user_id == current_user.id or await db.scalar(
        select(Follow.id).where(
            Follow.follower_id == current_user.id, Follow.followed_id == post.user_id
        )
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow this user to react.")
    existing = await db.scalar(
        select(PostReaction).where(
            PostReaction.post_id == post_id, PostReaction.user_id == current_user.id
        )
    )
    if not existing:
        db.add(PostReaction(post_id=post_id, user_id=current_user.id))
        await db.commit()


@router.delete("/posts/{post_id}/reaction", status_code=204)
async def remove_reaction(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    reaction = await db.scalar(
        select(PostReaction).where(
            PostReaction.post_id == post_id, PostReaction.user_id == current_user.id
        )
    )
    if reaction:
        await db.delete(reaction)
        await db.commit()


def profile_response(user: User, stats: UserStats) -> ProfileRead:
    return ProfileRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        gamification=gamification_snapshot(stats.xp_total, stats.current_streak),
    )
