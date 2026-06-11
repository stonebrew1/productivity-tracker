from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.category import Category
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.models.user import User
from app.schemas.stats import AnalyticsInterval, AnalyticsReport, StatsRead
from app.services.analytics_service import aggregate_task_events
from app.services.stats_service import recalculate_stats


router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatsRead)
async def read_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsRead:
    stats = await recalculate_stats(current_user.id, db)
    by_priority_rows = await db.execute(
        select(Task.priority, func.count()).where(Task.user_id == current_user.id).group_by(Task.priority)
    )
    by_status_rows = await db.execute(
        select(Task.status, func.count()).where(Task.user_id == current_user.id).group_by(Task.status)
    )
    total = stats.total_tasks
    completed = stats.completed_tasks
    return StatsRead(
        total_tasks=total,
        completed_tasks=completed,
        current_streak=stats.current_streak,
        completion_rate=round((completed / total) * 100, 2) if total else 0,
        by_priority={priority.value: count for priority, count in by_priority_rows.all()},
        by_status={status.value: count for status, count in by_status_rows.all()},
    )


@router.get("/analytics", response_model=AnalyticsReport)
async def read_analytics(
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=29)),
    date_to: date = Query(default_factory=date.today),
    interval: AnalyticsInterval = AnalyticsInterval.DAY,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsReport:
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be later than date_to.",
        )
    if (date_to - date_from).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analytics range cannot exceed 367 days.",
        )

    range_start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    range_end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
    events = await db.scalars(
        select(TaskEvent)
        .where(
            TaskEvent.user_id == current_user.id,
            TaskEvent.occurred_at >= range_start,
            TaskEvent.occurred_at < range_end,
        )
        .order_by(TaskEvent.occurred_at)
    )
    categories = await db.execute(
        select(Category.id, Category.name).where(Category.user_id == current_user.id)
    )
    category_names = {str(category_id): name for category_id, name in categories.all()}
    return aggregate_task_events(
        events=list(events),
        date_from=date_from,
        date_to=date_to,
        interval=interval,
        category_names=category_names,
    )
