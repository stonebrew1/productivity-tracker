from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember, GroupMilestone, GroupTask, ProductivityGroup
from app.models.task import TaskStatus
from app.schemas.group import GroupMilestoneCreate, GroupMilestoneRead, GroupMilestoneUpdate


async def milestone_read(
    milestone: GroupMilestone, viewer_id: UUID, db: AsyncSession
) -> GroupMilestoneRead:
    membership = await db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == milestone.group_id,
            GroupMember.user_id == viewer_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    task_count = await db.scalar(
        select(func.count()).select_from(GroupTask).where(GroupTask.milestone_id == milestone.id)
    ) or 0
    completed_count = await db.scalar(
        select(func.count()).select_from(GroupTask).where(
            GroupTask.milestone_id == milestone.id,
            GroupTask.status == TaskStatus.DONE,
        )
    ) or 0
    progress = round((completed_count / task_count) * 100) if task_count else 0
    return GroupMilestoneRead(
        id=milestone.id,
        group_id=milestone.group_id,
        title=milestone.title,
        description=milestone.description,
        target_date=milestone.target_date,
        created_at=milestone.created_at,
        task_count=task_count,
        completed_task_count=completed_count,
        progress_percent=progress,
        is_complete=task_count > 0 and completed_count == task_count,
        can_manage=membership.role == "leader",
    )


async def list_milestones(
    group_id: UUID, viewer_id: UUID, db: AsyncSession
) -> list[GroupMilestoneRead]:
    membership = await db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == viewer_id,
        )
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    milestones = list(
        await db.scalars(
            select(GroupMilestone)
            .where(GroupMilestone.group_id == group_id)
            .order_by(GroupMilestone.target_date.asc().nulls_last(), GroupMilestone.created_at.asc())
        )
    )
    return [await milestone_read(item, viewer_id, db) for item in milestones]


async def create_milestone(
    group_id: UUID, payload: GroupMilestoneCreate, leader_id: UUID, db: AsyncSession
) -> GroupMilestoneRead:
    await require_group_leader(group_id, leader_id, db)
    milestone = GroupMilestone(**payload.model_dump(), group_id=group_id)
    db.add(milestone)
    await db.flush()
    from app.services.group_activity_service import log_group_activity

    await log_group_activity(
        group_id,
        leader_id,
        "milestone_created",
        f"Created the milestone: {milestone.title}",
        db,
        source_key=f"group-milestone:{milestone.id}:created",
        created_at=milestone.created_at,
    )
    await db.commit()
    await db.refresh(milestone)
    return await milestone_read(milestone, leader_id, db)


async def update_milestone(
    milestone_id: UUID, payload: GroupMilestoneUpdate, leader_id: UUID, db: AsyncSession
) -> GroupMilestoneRead:
    milestone = await db.get(GroupMilestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")
    await require_group_leader(milestone.group_id, leader_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(milestone, field, value)
    await db.commit()
    await db.refresh(milestone)
    return await milestone_read(milestone, leader_id, db)


async def delete_milestone(milestone_id: UUID, leader_id: UUID, db: AsyncSession) -> None:
    milestone = await db.get(GroupMilestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found.")
    await require_group_leader(milestone.group_id, leader_id, db)
    await db.execute(
        update(GroupTask).where(GroupTask.milestone_id == milestone.id).values(milestone_id=None)
    )
    await db.delete(milestone)
    await db.commit()


async def require_group_leader(
    group_id: UUID, leader_id: UUID, db: AsyncSession
) -> ProductivityGroup:
    group = await db.get(ProductivityGroup, group_id)
    if not group or group.leader_id != leader_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group leader access required.")
    return group
