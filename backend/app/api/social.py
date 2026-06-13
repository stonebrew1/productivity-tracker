from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.social import (
    ActivityPost,
    Challenge,
    ChallengeMember,
    Friendship,
    Notification,
    PostComment,
    PostReaction,
    XpAward,
)
from app.models.user import User
from app.models.user_stats import UserStats
from app.schemas.social import (
    CommentCreate,
    CommentRead,
    ChallengeRead,
    CommitmentInvite,
    CommitmentRead,
    FeedAuthor,
    FeedPostRead,
    LeaderboardEntryRead,
    NotificationRead,
    PersonRead,
    ProfileRead,
)
from app.schemas.user import ProfileUpdate
from app.services.gamification_service import award_quest_rewards, gamification_snapshot, level_from_xp
from app.services.challenge_service import challenge_snapshot, list_challenges
from app.services.accountability_service import (
    cancel_commitment,
    invite_partner,
    list_commitments,
    respond_to_commitment,
)
from app.services.stats_service import ensure_stats
from app.services.friendship_service import are_friends, friend_ids_query, friendship_between


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
    friendships = list(
        await db.scalars(
            select(Friendship).where(
                or_(
                    Friendship.requester_id == current_user.id,
                    Friendship.addressee_id == current_user.id,
                )
            )
        )
    )
    relationship_by_user = {
        friendship.addressee_id if friendship.requester_id == current_user.id else friendship.requester_id:
        (
            "friends"
            if friendship.status == "accepted"
            else "pending_sent"
            if friendship.requester_id == current_user.id
            else "pending_received"
        )
        for friendship in friendships
    }
    rows = (
        await db.execute(
            select(User, UserStats, func.max(ActivityPost.created_at))
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .outerjoin(ActivityPost, ActivityPost.user_id == User.id)
            .where(User.id != current_user.id)
            .group_by(User.id, UserStats.id)
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
            current_streak=stats.current_streak if stats else 0,
            last_active_at=last_active_at,
            relationship_status=relationship_by_user.get(user.id, "none"),
            relationship_id=next(
                (
                    friendship.id
                    for friendship in friendships
                    if user.id in {friendship.requester_id, friendship.addressee_id}
                ),
                None,
            ),
        )
        for user, stats, last_active_at in rows
    ]


@router.get("/leaderboard", response_model=list[LeaderboardEntryRead])
async def read_leaderboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardEntryRead]:
    now = datetime.now(timezone.utc)
    week_start = datetime.combine(
        (now - timedelta(days=now.weekday())).date(),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    friend_ids = friend_ids_query(current_user.id)
    rows = (
        await db.execute(
            select(
                User,
                UserStats,
                func.coalesce(func.sum(XpAward.amount), 0).label("weekly_xp"),
            )
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .outerjoin(
                XpAward,
                (XpAward.user_id == User.id) & (XpAward.awarded_at >= week_start),
            )
            .where(or_(User.id == current_user.id, User.id.in_(friend_ids)))
            .group_by(User.id, UserStats.id)
            .order_by(
                func.coalesce(func.sum(XpAward.amount), 0).desc(),
                User.display_name.asc().nulls_last(),
            )
        )
    ).all()
    return [
        LeaderboardEntryRead(
            rank=index,
            user_id=user.id,
            display_name=user.display_name,
            email=user.email,
            avatar_url=user.avatar_url,
            level=level_from_xp(stats.xp_total if stats else 0),
            current_streak=stats.current_streak if stats else 0,
            weekly_xp=int(weekly_xp),
            is_current_user=user.id == current_user.id,
        )
        for index, (user, stats, weekly_xp) in enumerate(rows, start=1)
    ]


@router.get("/challenges", response_model=list[ChallengeRead])
async def read_challenges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChallengeRead]:
    return await list_challenges(current_user.id, db)


@router.post("/challenges/{challenge_id}/join", response_model=ChallengeRead)
async def join_challenge(
    challenge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeRead:
    challenge = await db.get(Challenge, challenge_id)
    now = datetime.now(timezone.utc)
    if not challenge or not challenge.is_active or challenge.ends_at <= now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")
    current_state = await challenge_snapshot(challenge, current_user.id, db)
    if current_state.completed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed challenges cannot be joined.")
    existing = await db.scalar(
        select(ChallengeMember).where(
            ChallengeMember.challenge_id == challenge.id,
            ChallengeMember.user_id == current_user.id,
        )
    )
    if not existing:
        db.add(
            ChallengeMember(
                challenge_id=challenge.id,
                user_id=current_user.id,
                joined_at=max(now, challenge.starts_at),
            )
        )
        await db.commit()
    return await challenge_snapshot(challenge, current_user.id, db)


@router.delete("/challenges/{challenge_id}/join", status_code=204)
async def leave_challenge(
    challenge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    challenge = await db.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found.")
    snapshot = await challenge_snapshot(challenge, current_user.id, db)
    if snapshot.completed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed challenges cannot be left.")
    membership = await db.scalar(
        select(ChallengeMember).where(
            ChallengeMember.challenge_id == challenge.id,
            ChallengeMember.user_id == current_user.id,
        )
    )
    if membership:
        await db.delete(membership)
        await db.commit()


@router.get("/commitments", response_model=list[CommitmentRead])
async def read_commitments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommitmentRead]:
    return await list_commitments(current_user.id, db)


@router.post("/tasks/{task_id}/accountability", response_model=CommitmentRead, status_code=201)
async def create_commitment(
    task_id: UUID,
    payload: CommitmentInvite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitmentRead:
    return await invite_partner(task_id, payload.partner_id, current_user, db)


@router.post("/commitments/{commitment_id}/accept", response_model=CommitmentRead)
async def accept_commitment(
    commitment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitmentRead:
    return await respond_to_commitment(commitment_id, current_user.id, True, db)


@router.post("/commitments/{commitment_id}/decline", response_model=CommitmentRead)
async def decline_commitment(
    commitment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommitmentRead:
    return await respond_to_commitment(commitment_id, current_user.id, False, db)


@router.delete("/commitments/{commitment_id}", status_code=204)
async def delete_commitment(
    commitment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await cancel_commitment(commitment_id, current_user.id, db)


@router.post("/people/{user_id}/friend-request", status_code=204)
async def send_friend_request(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot add yourself.")
    if not await db.get(User, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    existing = await friendship_between(current_user.id, user_id, db)
    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already friends.")
        if existing.requester_id == user_id:
            existing.status = "accepted"
            existing.responded_at = datetime.now(timezone.utc)
            db.add(
                Notification(
                    kind="friend_accepted",
                    message="accepted your friend request",
                    recipient_id=user_id,
                    actor_id=current_user.id,
                    friendship_id=existing.id,
                )
            )
            await db.commit()
            return
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Friend request already sent.")
    friendship = Friendship(
        requester_id=current_user.id,
        addressee_id=user_id,
        status="pending",
    )
    db.add(friendship)
    await db.flush()
    db.add(
        Notification(
            kind="friend_request",
            message="sent you a friend request",
            recipient_id=user_id,
            actor_id=current_user.id,
            friendship_id=friendship.id,
        )
    )
    await db.commit()


@router.post("/friend-requests/{friendship_id}/accept", status_code=204)
async def accept_friend_request(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    friendship = await db.get(Friendship, friendship_id)
    if not friendship or friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found.")
    if friendship.status == "accepted":
        await mark_friend_request_notifications_resolved(friendship.id, current_user.id, db)
        await db.commit()
        return
    if friendship.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found.")
    friendship.status = "accepted"
    friendship.responded_at = datetime.now(timezone.utc)
    await mark_friend_request_notifications_resolved(friendship.id, current_user.id, db)
    db.add(
        Notification(
            kind="friend_accepted",
            message="accepted your friend request",
            recipient_id=friendship.requester_id,
            actor_id=current_user.id,
            friendship_id=friendship.id,
        )
    )
    await db.commit()


@router.delete("/friend-requests/{friendship_id}", status_code=204)
async def decline_friend_request(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    friendship = await db.get(Friendship, friendship_id)
    if not friendship or current_user.id not in {
        friendship.requester_id,
        friendship.addressee_id,
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend request not found.")
    await db.delete(friendship)
    await db.commit()


@router.delete("/people/{user_id}/friendship", status_code=204)
async def remove_friend(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    friendship = await friendship_between(current_user.id, user_id, db)
    if friendship:
        await db.delete(friendship)
        await db.commit()


@router.get("/feed", response_model=list[FeedPostRead])
async def read_feed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeedPostRead]:
    friend_ids = friend_ids_query(current_user.id)
    rows = (
        await db.execute(
            select(ActivityPost, User, UserStats)
            .join(User, User.id == ActivityPost.user_id)
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .where(or_(ActivityPost.user_id == current_user.id, ActivityPost.user_id.in_(friend_ids)))
            .order_by(ActivityPost.created_at.desc())
            .limit(50)
        )
    ).all()
    post_ids = [post.id for post, _, _ in rows]
    reaction_counts: dict[UUID, int] = {}
    comment_counts: dict[UUID, int] = {}
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
        comment_counts = dict(
            (
                await db.execute(
                    select(PostComment.post_id, func.count())
                    .where(PostComment.post_id.in_(post_ids))
                    .group_by(PostComment.post_id)
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
            comments_count=comment_counts.get(post.id, 0),
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
    if post.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Encouragement is reserved for other people's progress.",
        )
    allowed = post.user_id == current_user.id or await are_friends(
        current_user.id, post.user_id, db
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Add this person as a friend to react.")
    existing = await db.scalar(
        select(PostReaction).where(
            PostReaction.post_id == post_id, PostReaction.user_id == current_user.id
        )
    )
    if not existing:
        db.add(PostReaction(post_id=post_id, user_id=current_user.id))
        db.add(
            Notification(
                kind="reaction",
                message=f"encouraged your completion of {post.task_title}",
                recipient_id=post.user_id,
                actor_id=current_user.id,
                post_id=post.id,
            )
        )
        await db.flush()
        await award_quest_rewards(current_user.id, db)
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


@router.get("/posts/{post_id}/comments", response_model=list[CommentRead])
async def read_comments(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommentRead]:
    post = await visible_post(post_id, current_user.id, db)
    rows = (
        await db.execute(
            select(PostComment, User, UserStats)
            .join(User, User.id == PostComment.user_id)
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .where(PostComment.post_id == post.id)
            .order_by(PostComment.created_at.asc())
            .limit(100)
        )
    ).all()
    return [
        CommentRead(
            id=comment.id,
            content=comment.content,
            created_at=comment.created_at,
            author=feed_author(user, stats),
            can_delete=comment.user_id == current_user.id,
        )
        for comment, user, stats in rows
    ]


@router.post("/posts/{post_id}/comments", response_model=CommentRead, status_code=201)
async def create_comment(
    post_id: UUID,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    post = await visible_post(post_id, current_user.id, db)
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment cannot be empty.")
    comment = PostComment(
        content=content,
        post_id=post.id,
        user_id=current_user.id,
    )
    db.add(comment)
    if post.user_id != current_user.id:
        db.add(
            Notification(
                kind="comment",
                message=f"commented on your completion of {post.task_title}",
                recipient_id=post.user_id,
                actor_id=current_user.id,
                post_id=post.id,
            )
        )
    await db.flush()
    await award_quest_rewards(current_user.id, db)
    stats = await ensure_stats(current_user.id, db)
    await db.commit()
    await db.refresh(comment)
    return CommentRead(
        id=comment.id,
        content=comment.content,
        created_at=comment.created_at,
        author=feed_author(current_user, stats),
        can_delete=True,
    )


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    comment = await db.get(PostComment, comment_id)
    if not comment or comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    await db.delete(comment)
    await db.commit()


@router.get("/notifications", response_model=list[NotificationRead])
async def read_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationRead]:
    rows = (
        await db.execute(
            select(Notification, User, UserStats, Friendship)
            .join(User, User.id == Notification.actor_id)
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .outerjoin(Friendship, Friendship.id == Notification.friendship_id)
            .where(Notification.recipient_id == current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        NotificationRead(
            id=notification.id,
            kind=notification.kind,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
            post_id=notification.post_id,
            friendship_id=notification.friendship_id,
            friendship_status=friendship.status if friendship else None,
            actor=feed_author(actor, stats),
        )
        for notification, actor, stats, friendship in rows
    ]


@router.post("/notifications/read", status_code=204)
async def mark_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    notifications = list(
        await db.scalars(
            select(Notification).where(
                Notification.recipient_id == current_user.id,
                Notification.is_read.is_(False),
            )
        )
    )
    for notification in notifications:
        notification.is_read = True
    await db.commit()


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    notification = await db.get(Notification, notification_id)
    if not notification or notification.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    notification.is_read = True
    await db.commit()


async def mark_friend_request_notifications_resolved(
    friendship_id: UUID,
    recipient_id: UUID,
    db: AsyncSession,
) -> None:
    notifications = list(
        await db.scalars(
            select(Notification).where(
                Notification.friendship_id == friendship_id,
                Notification.recipient_id == recipient_id,
                Notification.kind == "friend_request",
            )
        )
    )
    for notification in notifications:
        notification.is_read = True


def profile_response(user: User, stats: UserStats) -> ProfileRead:
    return ProfileRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        gamification=gamification_snapshot(stats.xp_total, stats.current_streak),
    )


def feed_author(user: User, stats: UserStats | None) -> FeedAuthor:
    return FeedAuthor(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        avatar_url=user.avatar_url,
        level=level_from_xp(stats.xp_total if stats else 0),
    )


async def visible_post(post_id: UUID, user_id: UUID, db: AsyncSession) -> ActivityPost:
    post = await db.get(ActivityPost, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    if post.user_id != user_id:
        if not await are_friends(user_id, post.user_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Add this person as a friend first.")
    return post
