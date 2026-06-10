from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.task import Task, TaskStatus
from app.models.task_event import TaskEventType
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.achievement_service import check_and_award
from app.services.stats_service import recalculate_stats
from app.services.task_event_service import build_changes, record_task_event, serialize_event_value, task_snapshot


TRACKED_TASK_FIELDS = {
    "title",
    "description",
    "priority",
    "status",
    "deadline",
    "category_id",
    "parent_id",
}


async def validate_task_links(payload: TaskCreate | TaskUpdate, current_user: User, db: AsyncSession) -> None:
    if payload.category_id:
        category = await db.get(Category, payload.category_id)
        if not category or category.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category.")
    if payload.parent_id:
        parent = await db.get(Task, payload.parent_id)
        if not parent or parent.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent task.")


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
    await validate_task_links(payload, current_user, db)

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
            await check_and_award(current_user.id, task, db)
        elif "status" in changes:
            event_type = TaskEventType.STATUS_CHANGED
        else:
            event_type = TaskEventType.UPDATED
        await record_task_event(db, task, event_type, changes)

    await recalculate_stats(current_user.id, db)
    await db.commit()
    await db.refresh(task)
    return task


async def complete_task(task_id: UUID, current_user: User, db: AsyncSession) -> tuple[Task, list]:
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
    achievements = await check_and_award(current_user.id, task, db)
    await recalculate_stats(current_user.id, db)
    await db.commit()
    await db.refresh(task)
    for achievement in achievements:
        await db.refresh(achievement)
    return task, achievements


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
    await db.delete(task)
    await db.flush()
    await recalculate_stats(current_user.id, db)
    await db.commit()
