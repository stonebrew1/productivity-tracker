from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.task import Task, TaskStatus, TaskVisibility
from app.models.social import AccountabilityCommitment, ActivityPost
from app.models.task_event import TaskEventType
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.achievement_service import check_and_award
from app.services.accountability_service import award_accountability_bonus
from app.services.challenge_service import award_challenge_rewards
from app.services.gamification_service import award_quest_rewards, award_task_completion, sync_activity_post
from app.services.stats_service import recalculate_stats
from app.services.task_event_service import build_changes, record_task_event, serialize_event_value, task_snapshot


TRACKED_TASK_FIELDS = {
    "title",
    "description",
    "priority",
    "status",
    "deadline",
    "scheduled_for",
    "estimated_minutes",
    "is_focus",
    "visibility",
    "category_id",
    "parent_id",
}


async def validate_task_links(
    payload: TaskCreate | TaskUpdate,
    current_user: User,
    db: AsyncSession,
    task_id: UUID | None = None,
) -> None:
    if payload.category_id:
        category = await db.get(Category, payload.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category.")
    if payload.parent_id:
        if payload.parent_id == task_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A task cannot be its own parent.")
        parent = await db.get(Task, payload.parent_id)
        if not parent or parent.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent task.")
        ancestor = parent
        visited: set[UUID] = set()
        while ancestor.parent_id:
            if ancestor.id in visited or ancestor.parent_id == task_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Task hierarchy cannot contain a cycle.",
                )
            visited.add(ancestor.id)
            next_ancestor = await db.get(Task, ancestor.parent_id)
            if not next_ancestor or next_ancestor.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task hierarchy.")
            ancestor = next_ancestor


async def create_task(payload: TaskCreate, current_user: User, db: AsyncSession) -> Task:
    await validate_task_links(payload, current_user, db)
    task = Task(**payload.model_dump(), user_id=current_user.id)
    db.add(task)
    await db.flush()
    await record_task_event(
        db,
        task,
        TaskEventType.CREATED,
        build_changes({}, task_snapshot(task, TRACKED_TASK_FIELDS)),
    )
    await recalculate_stats(current_user.id, db)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(task_id: UUID, payload: TaskUpdate, current_user: User, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    await validate_task_links(payload, current_user, db, task.id)
    if payload.visibility == TaskVisibility.PRIVATE:
        active_commitment = await db.scalar(
            select(AccountabilityCommitment.id).where(
                AccountabilityCommitment.task_id == task.id,
                AccountabilityCommitment.status.in_(["pending", "accepted"]),
            )
        )
        if active_commitment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cancel the accountability commitment before making this task private.",
            )

    before = task_snapshot(task, TRACKED_TASK_FIELDS)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    if payload.status == TaskStatus.DONE and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    if payload.status and payload.status != TaskStatus.DONE:
        task.completed_at = None

    changes = build_changes(before, task_snapshot(task, TRACKED_TASK_FIELDS))
    if changes:
        if "status" in changes and task.status == TaskStatus.DONE:
            event_type = TaskEventType.COMPLETED
            await award_task_completion(task, db)
            await recalculate_stats(current_user.id, db)
            await check_and_award(current_user.id, task, db)
            await award_quest_rewards(current_user.id, db)
            await award_challenge_rewards(task, db)
            await award_accountability_bonus(task, db)
        elif "status" in changes:
            event_type = TaskEventType.STATUS_CHANGED
        else:
            event_type = TaskEventType.UPDATED
        await record_task_event(db, task, event_type, changes)
        if "visibility" in changes or "title" in changes:
            await sync_activity_post(task, db)

    await recalculate_stats(current_user.id, db)
    await db.commit()
    await db.refresh(task)
    return task


async def complete_task(task_id: UUID, current_user: User, db: AsyncSession) -> tuple[Task, list, int]:
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.status == TaskStatus.DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is already completed.")

    previous_status = task.status
    task.status = TaskStatus.DONE
    task.completed_at = datetime.now(timezone.utc)
    await record_task_event(
        db,
        task,
        TaskEventType.COMPLETED,
        {"status": {"from": previous_status.value, "to": TaskStatus.DONE.value}},
    )
    xp_awarded = await award_task_completion(task, db)
    await recalculate_stats(current_user.id, db)
    achievements = await check_and_award(current_user.id, task, db)
    await award_quest_rewards(current_user.id, db)
    await award_challenge_rewards(task, db)
    await award_accountability_bonus(task, db)
    await db.commit()
    await db.refresh(task)
    for achievement in achievements:
        await db.refresh(achievement)
    return task, achievements, xp_awarded


async def delete_task(task_id: UUID, current_user: User, db: AsyncSession) -> None:
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await record_task_event(
        db,
        task,
        TaskEventType.DELETED,
        {
            "snapshot": {
                field: serialize_event_value(value)
                for field, value in task_snapshot(task, TRACKED_TASK_FIELDS).items()
            }
        },
    )
    post = await db.scalar(select(ActivityPost).where(ActivityPost.task_id == task.id))
    if post:
        await db.delete(post)
    await db.delete(task)
    await db.flush()
    await recalculate_stats(current_user.id, db)
    await db.commit()
