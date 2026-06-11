from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

from app.models.task_event import TaskEventType
from app.schemas.stats import AnalyticsInterval, AnalyticsReport, TrendPoint


class AnalyticsEvent(Protocol):
    event_type: TaskEventType
    changes: dict
    occurred_at: datetime


def bucket_start(value: date, interval: AnalyticsInterval) -> date:
    if interval == AnalyticsInterval.WEEK:
        return value - timedelta(days=value.weekday())
    if interval == AnalyticsInterval.MONTH:
        return value.replace(day=1)
    return value


def next_bucket(value: date, interval: AnalyticsInterval) -> date:
    if interval == AnalyticsInterval.WEEK:
        return value + timedelta(days=7)
    if interval == AnalyticsInterval.MONTH:
        if value.month == 12:
            return value.replace(year=value.year + 1, month=1, day=1)
        return value.replace(month=value.month + 1, day=1)
    return value + timedelta(days=1)


def parse_snapshot_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def aggregate_task_events(
    events: Iterable[AnalyticsEvent],
    date_from: date,
    date_to: date,
    interval: AnalyticsInterval,
    category_names: dict[str, str] | None = None,
) -> AnalyticsReport:
    category_names = category_names or {}
    period = bucket_start(date_from, interval)
    final_period = bucket_start(date_to, interval)
    trend_by_period: dict[date, dict[str, int]] = {}
    while period <= final_period:
        trend_by_period[period] = {"created": 0, "completed": 0, "deleted": 0}
        period = next_bucket(period, interval)

    created_tasks = 0
    completed_tasks = 0
    deleted_tasks = 0
    on_time_completed = 0
    overdue_completed = 0
    without_deadline_completed = 0
    by_priority: dict[str, int] = {}
    by_category: dict[str, int] = {}

    for event in events:
        event_date = event.occurred_at.date()
        if not date_from <= event_date <= date_to:
            continue
        bucket = trend_by_period[bucket_start(event_date, interval)]

        if event.event_type == TaskEventType.CREATED:
            created_tasks += 1
            bucket["created"] += 1
        elif event.event_type == TaskEventType.DELETED:
            deleted_tasks += 1
            bucket["deleted"] += 1
        elif event.event_type == TaskEventType.COMPLETED:
            completed_tasks += 1
            bucket["completed"] += 1
            snapshot = event.changes.get("_snapshot", {})

            priority = snapshot.get("priority") or "unknown"
            by_priority[priority] = by_priority.get(priority, 0) + 1

            category_id = snapshot.get("category_id")
            category = category_names.get(category_id, "Uncategorized" if not category_id else "Deleted category")
            by_category[category] = by_category.get(category, 0) + 1

            deadline = parse_snapshot_datetime(snapshot.get("deadline"))
            completed_at = parse_snapshot_datetime(snapshot.get("completed_at"))
            if not deadline:
                without_deadline_completed += 1
            elif completed_at and completed_at <= deadline:
                on_time_completed += 1
            else:
                overdue_completed += 1

    trend = [
        TrendPoint(period=period, **counts)
        for period, counts in sorted(trend_by_period.items())
    ]
    return AnalyticsReport(
        date_from=date_from,
        date_to=date_to,
        interval=interval,
        created_tasks=created_tasks,
        completed_tasks=completed_tasks,
        deleted_tasks=deleted_tasks,
        on_time_completed=on_time_completed,
        overdue_completed=overdue_completed,
        without_deadline_completed=without_deadline_completed,
        by_priority=by_priority,
        by_category=by_category,
        trend=trend,
    )
