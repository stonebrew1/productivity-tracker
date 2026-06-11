from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.task import Task, TaskStatus
from app.models.task_event import TaskEvent, TaskEventType
from app.models.user import User
from app.schemas.task import TaskCompleteResponse, TaskCreate, TaskRead, TaskUpdate
from app.schemas.task_event import TaskEventPage
from app.services.task_service import complete_task, create_task, delete_task as delete_task_service, update_task


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Task]:
    query = select(Task).where(Task.user_id == current_user.id).order_by(Task.deadline.asc().nulls_last(), Task.title)
    if status_filter:
        query = query.where(Task.status == status_filter)
    result = await db.scalars(query)
    return list(result)


@router.post("", response_model=TaskRead, status_code=201)
async def create_task_route(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    return await create_task(payload, current_user, db)


@router.get("/history", response_model=TaskEventPage)
async def list_task_history(
    event_type: TaskEventType | None = None,
    task_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskEventPage:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be later than date_to.",
        )

    filters = [TaskEvent.user_id == current_user.id]
    if event_type:
        filters.append(TaskEvent.event_type == event_type)
    if task_id:
        filters.append(TaskEvent.task_id == task_id)
    if date_from:
        filters.append(TaskEvent.occurred_at >= date_from)
    if date_to:
        filters.append(TaskEvent.occurred_at <= date_to)

    total = await db.scalar(select(func.count()).select_from(TaskEvent).where(*filters))
    result = await db.scalars(
        select(TaskEvent)
        .where(*filters)
        .order_by(TaskEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return TaskEventPage(items=list(result), total=total or 0, limit=limit, offset=offset)


@router.put("/{task_id}", response_model=TaskRead)
async def update_task_route(
    task_id: UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    return await update_task(task_id, payload, current_user, db)


@router.post("/{task_id}/complete", response_model=TaskCompleteResponse)
async def complete_task_route(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskCompleteResponse:
    task, achievements, xp_awarded = await complete_task(task_id, current_user, db)
    return TaskCompleteResponse(task=task, achievements=achievements, xp_awarded=xp_awarded)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_task_service(task_id, current_user, db)
