from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember, GroupMilestone, GroupTask, ProductivityGroup
from app.models.social import Notification
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.group import GroupTaskCreate, GroupTaskRead, GroupTaskUpdate


async def require_membership(group_id: UUID, user_id: UUID, db: AsyncSession) -> GroupMember:
    membership = await db.scalar(
        select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    return membership


async def task_read(task: GroupTask, viewer_id: UUID, db: AsyncSession) -> GroupTaskRead:
    membership = await require_membership(task.group_id, viewer_id, db)
    assignee = await db.get(User, task.assigned_to_id)
    milestone = await db.get(GroupMilestone, task.milestone_id) if task.milestone_id else None
    return GroupTaskRead(
        id=task.id,
        group_id=task.group_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        deadline=task.deadline,
        created_at=task.created_at,
        completed_at=task.completed_at,
        assigned_to_id=task.assigned_to_id,
        assignee_name=(assignee.display_name or assignee.email.split("@")[0]) if assignee else "Unknown",
        created_by_id=task.created_by_id,
        milestone_id=task.milestone_id,
        milestone_title=milestone.title if milestone else None,
        can_manage=membership.role == "leader",
        can_update_status=membership.role == "leader" or task.assigned_to_id == viewer_id,
    )


async def list_group_tasks(group_id: UUID, user_id: UUID, db: AsyncSession) -> list[GroupTaskRead]:
    await require_membership(group_id, user_id, db)
    tasks = list(
        await db.scalars(
            select(GroupTask)
            .where(GroupTask.group_id == group_id)
            .order_by(GroupTask.deadline.asc().nulls_last(), GroupTask.created_at.desc())
        )
    )
    return [await task_read(task, user_id, db) for task in tasks]


async def create_group_task(
    group_id: UUID, payload: GroupTaskCreate, leader: User, db: AsyncSession
) -> GroupTaskRead:
    group = await db.get(ProductivityGroup, group_id)
    if not group or group.leader_id != leader.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group leader access required.")
    assignee_membership = await db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == payload.assigned_to_id,
        )
    )
    if not assignee_membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee is not a group member.")
    await validate_milestone(payload.milestone_id, group_id, db)
    task = GroupTask(**payload.model_dump(), group_id=group_id, created_by_id=leader.id)
    db.add(task)
    if payload.assigned_to_id != leader.id:
        db.add(
            Notification(
                kind="group",
                message=f"assigned you a group task: {payload.title}",
                recipient_id=payload.assigned_to_id,
                actor_id=leader.id,
            )
        )
    await db.commit()
    await db.refresh(task)
    return await task_read(task, leader.id, db)


async def update_group_task(
    task_id: UUID, payload: GroupTaskUpdate, user: User, db: AsyncSession
) -> GroupTaskRead:
    task = await db.get(GroupTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group task not found.")
    membership = await require_membership(task.group_id, user.id, db)
    changes = payload.model_dump(exclude_unset=True)
    previous_assignee_id = task.assigned_to_id
    previous_status = task.status
    if membership.role != "leader":
        if set(changes) - {"status"} or task.assigned_to_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the group leader can edit this task.")
    if "assigned_to_id" in changes:
        assignee_membership = await db.scalar(
            select(GroupMember.id).where(
                GroupMember.group_id == task.group_id,
                GroupMember.user_id == changes["assigned_to_id"],
            )
        )
        if not assignee_membership:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee is not a group member.")
    if "milestone_id" in changes:
        await validate_milestone(changes["milestone_id"], task.group_id, db)
    for field, value in changes.items():
        setattr(task, field, value)
    if payload.status == TaskStatus.DONE and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    elif payload.status and payload.status != TaskStatus.DONE:
        task.completed_at = None
    if task.assigned_to_id != previous_assignee_id and task.assigned_to_id != user.id:
        db.add(
            Notification(
                kind="group",
                message=f"assigned you a group task: {task.title}",
                recipient_id=task.assigned_to_id,
                actor_id=user.id,
            )
        )
    if (
        task.status == TaskStatus.DONE
        and previous_status != TaskStatus.DONE
        and membership.role != "leader"
    ):
        group = await db.get(ProductivityGroup, task.group_id)
        if group:
            db.add(
                Notification(
                    kind="group",
                    message=f"completed the group task: {task.title}",
                    recipient_id=group.leader_id,
                    actor_id=user.id,
                )
            )
    await db.commit()
    await db.refresh(task)
    return await task_read(task, user.id, db)


async def delete_group_task(task_id: UUID, leader_id: UUID, db: AsyncSession) -> None:
    task = await db.get(GroupTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group task not found.")
    group = await db.get(ProductivityGroup, task.group_id)
    if not group or group.leader_id != leader_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group leader access required.")
    await db.delete(task)
    await db.commit()


async def validate_milestone(
    milestone_id: UUID | None, group_id: UUID, db: AsyncSession
) -> None:
    if not milestone_id:
        return
    milestone = await db.get(GroupMilestone, milestone_id)
    if not milestone or milestone.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid group milestone.")
