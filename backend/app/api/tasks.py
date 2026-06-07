from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCompleteResponse, TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import complete_task, create_task, update_task


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
    task, achievements = await complete_task(task_id, current_user, db)
    return TaskCompleteResponse(task=task, achievements=achievements)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await db.get(Task, task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    await db.delete(task)
    await db.commit()
