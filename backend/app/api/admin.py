from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.achievement import Achievement
from app.models.group import ProductivityGroup
from app.models.refresh_token import RefreshToken
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.schemas.admin import AdminSummary, AdminUserPage, AdminUserRead


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserPage:
    filters = []
    if query and query.strip():
        pattern = f"%{query.strip()}%"
        filters.append(or_(User.email.ilike(pattern), User.display_name.ilike(pattern)))

    total = await db.scalar(select(func.count()).select_from(User).where(*filters))
    rows = await db.execute(
        select(
            User,
            func.count(Task.id).label("total_tasks"),
            func.count(Task.id).filter(Task.status == TaskStatus.DONE).label("completed_tasks"),
        )
        .outerjoin(Task, Task.user_id == User.id)
        .where(*filters)
        .group_by(User.id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = [
        AdminUserRead(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            is_email_verified=user.is_email_verified,
            is_blocked=user.is_blocked,
            blocked_at=user.blocked_at,
            created_at=user.created_at,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
        )
        for user, total_tasks, completed_tasks in rows.all()
    ]
    return AdminUserPage(items=items, total=total or 0, limit=limit, offset=offset)


@router.post("/users/{user_id}/block", response_model=AdminUserRead)
async def block_user(
    user_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserRead:
    if user_id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot block your own account.")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrator accounts cannot be blocked.")

    user.is_blocked = True
    user.blocked_at = datetime.now(timezone.utc)
    active_tokens = list(
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    )
    for token in active_tokens:
        token.revoked_at = user.blocked_at
    await db.commit()
    return await admin_user_read(user, db)


@router.delete("/users/{user_id}/block", response_model=AdminUserRead)
async def unblock_user(
    user_id: UUID,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserRead:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.is_blocked = False
    user.blocked_at = None
    await db.commit()
    return await admin_user_read(user, db)


@router.get("/statistics", response_model=AdminSummary)
async def read_admin_statistics(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminSummary:
    total_users = int(await db.scalar(select(func.count()).select_from(User)) or 0)
    verified_users = int(
        await db.scalar(select(func.count()).select_from(User).where(User.is_email_verified.is_(True))) or 0
    )
    blocked_users = int(
        await db.scalar(select(func.count()).select_from(User).where(User.is_blocked.is_(True))) or 0
    )
    administrators = int(
        await db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)) or 0
    )
    total_tasks = int(await db.scalar(select(func.count()).select_from(Task)) or 0)
    completed_tasks = int(
        await db.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.DONE)) or 0
    )
    status_rows = await db.execute(select(Task.status, func.count()).group_by(Task.status))
    return AdminSummary(
        total_users=total_users,
        verified_users=verified_users,
        blocked_users=blocked_users,
        administrators=administrators,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        total_achievements=int(await db.scalar(select(func.count()).select_from(Achievement)) or 0),
        total_groups=int(await db.scalar(select(func.count()).select_from(ProductivityGroup)) or 0),
        completion_rate=round((completed_tasks / total_tasks) * 100, 2) if total_tasks else 0,
        tasks_by_status={task_status.value: count for task_status, count in status_rows.all()},
    )


async def admin_user_read(user: User, db: AsyncSession) -> AdminUserRead:
    total_tasks = int(
        await db.scalar(select(func.count()).select_from(Task).where(Task.user_id == user.id)) or 0
    )
    completed_tasks = int(
        await db.scalar(
            select(func.count()).select_from(Task).where(
                Task.user_id == user.id,
                Task.status == TaskStatus.DONE,
            )
        )
        or 0
    )
    return AdminUserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_email_verified=user.is_email_verified,
        is_blocked=user.is_blocked,
        blocked_at=user.blocked_at,
        created_at=user.created_at,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
    )
