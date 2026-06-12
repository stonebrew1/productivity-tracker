from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import (
    GroupActivity,
    GroupActivityComment,
    GroupMember,
    GroupMilestone,
    GroupTask,
    ProductivityGroup,
)
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.group import (
    GroupActivityAuthor,
    GroupActivityCommentRead,
    GroupActivityRead,
)
from app.services.group_task_service import require_membership


async def log_group_activity(
    group_id: UUID,
    user_id: UUID,
    kind: str,
    content: str,
    db: AsyncSession,
    source_key: str | None = None,
    created_at: datetime | None = None,
) -> GroupActivity | None:
    if source_key and await db.scalar(
        select(GroupActivity.id).where(GroupActivity.source_key == source_key)
    ):
        return None
    activity = GroupActivity(
        group_id=group_id,
        user_id=user_id,
        kind=kind,
        content=content,
        source_key=source_key,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(activity)
    return activity


async def sync_group_activity(group_id: UUID, db: AsyncSession) -> None:
    group = await db.get(ProductivityGroup, group_id)
    if not group:
        return
    members = list(
        await db.scalars(select(GroupMember).where(GroupMember.group_id == group_id))
    )
    for member in members:
        user = await db.get(User, member.user_id)
        if user:
            name = user.display_name or user.email.split("@")[0]
            await log_group_activity(
                group_id,
                member.user_id,
                "member_joined",
                f"{name} joined the group",
                db,
                source_key=f"group-member:{member.id}:joined",
                created_at=member.joined_at,
            )
    tasks = list(await db.scalars(select(GroupTask).where(GroupTask.group_id == group_id)))
    for task in tasks:
        await log_group_activity(
            group_id,
            task.created_by_id,
            "task_created",
            f"Created the task: {task.title}",
            db,
            source_key=f"group-task:{task.id}:created",
            created_at=task.created_at,
        )
        if task.status == TaskStatus.DONE and task.completed_at:
            await log_group_activity(
                group_id,
                task.assigned_to_id,
                "task_completed",
                f"Completed the task: {task.title}",
                db,
                source_key=f"group-task:{task.id}:completed",
                created_at=task.completed_at,
            )
    milestones = list(
        await db.scalars(select(GroupMilestone).where(GroupMilestone.group_id == group_id))
    )
    for milestone in milestones:
        await log_group_activity(
            group_id,
            group.leader_id,
            "milestone_created",
            f"Created the milestone: {milestone.title}",
            db,
            source_key=f"group-milestone:{milestone.id}:created",
            created_at=milestone.created_at,
        )
        if milestone.completed_at:
            await log_group_activity(
                group_id,
                group.leader_id,
                "milestone_reached",
                f"Reached the milestone: {milestone.title}",
                db,
                source_key=f"group-milestone:{milestone.id}:completed",
                created_at=milestone.completed_at,
            )


def activity_author(user: User) -> GroupActivityAuthor:
    return GroupActivityAuthor(
        id=user.id,
        display_name=user.display_name or user.email.split("@")[0],
        avatar_url=user.avatar_url,
    )


async def activity_read(
    activity: GroupActivity, viewer_id: UUID, leader_id: UUID, db: AsyncSession
) -> GroupActivityRead:
    user = await db.get(User, activity.user_id)
    rows = (
        await db.execute(
            select(GroupActivityComment, User)
            .join(User, User.id == GroupActivityComment.user_id)
            .where(GroupActivityComment.activity_id == activity.id)
            .order_by(GroupActivityComment.created_at.asc())
        )
    ).all()
    return GroupActivityRead(
        id=activity.id,
        kind=activity.kind,
        content=activity.content,
        created_at=activity.created_at,
        author=activity_author(user),
        comments=[
            GroupActivityCommentRead(
                id=comment.id,
                content=comment.content,
                created_at=comment.created_at,
                author=activity_author(author),
                can_delete=comment.user_id == viewer_id or viewer_id == leader_id,
            )
            for comment, author in rows
        ],
    )


async def list_group_activity(
    group_id: UUID, viewer_id: UUID, db: AsyncSession
) -> list[GroupActivityRead]:
    await require_membership(group_id, viewer_id, db)
    await sync_group_activity(group_id, db)
    await db.commit()
    group = await db.get(ProductivityGroup, group_id)
    activities = list(
        await db.scalars(
            select(GroupActivity)
            .where(GroupActivity.group_id == group_id)
            .order_by(GroupActivity.created_at.desc())
            .limit(50)
        )
    )
    return [await activity_read(item, viewer_id, group.leader_id, db) for item in activities]


async def create_group_update(
    group_id: UUID, content: str, user: User, db: AsyncSession
) -> GroupActivityRead:
    await require_membership(group_id, user.id, db)
    content = content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Update cannot be empty.")
    activity = await log_group_activity(
        group_id, user.id, "update", content, db
    )
    await db.commit()
    await db.refresh(activity)
    group = await db.get(ProductivityGroup, group_id)
    return await activity_read(activity, user.id, group.leader_id, db)


async def create_activity_comment(
    activity_id: UUID, content: str, user: User, db: AsyncSession
) -> GroupActivityCommentRead:
    activity = await db.get(GroupActivity, activity_id)
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found.")
    await require_membership(activity.group_id, user.id, db)
    content = content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comment cannot be empty.")
    comment = GroupActivityComment(
        activity_id=activity.id,
        user_id=user.id,
        content=content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return GroupActivityCommentRead(
        id=comment.id,
        content=comment.content,
        created_at=comment.created_at,
        author=activity_author(user),
        can_delete=True,
    )


async def delete_activity_comment(
    comment_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    comment = await db.get(GroupActivityComment, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    activity = await db.get(GroupActivity, comment.activity_id)
    group = await db.get(ProductivityGroup, activity.group_id)
    await require_membership(group.id, user_id, db)
    if comment.user_id != user_id and group.leader_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    await db.delete(comment)
    await db.commit()
