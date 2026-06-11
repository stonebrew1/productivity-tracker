from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.models.task_event import TaskEventType
from app.schemas.stats import AnalyticsInterval
from app.services.analytics_service import aggregate_task_events


def event(
    event_type: TaskEventType,
    occurred_at: datetime,
    snapshot: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        occurred_at=occurred_at,
        changes={"_snapshot": snapshot or {}},
    )


def test_aggregate_task_events_builds_weekly_report() -> None:
    events = [
        event(TaskEventType.CREATED, datetime(2026, 6, 1, 9, tzinfo=timezone.utc)),
        event(
            TaskEventType.COMPLETED,
            datetime(2026, 6, 3, 10, tzinfo=timezone.utc),
            {
                "priority": "high",
                "category_id": "category-1",
                "deadline": "2026-06-04T10:00:00",
                "completed_at": "2026-06-03T10:00:00+00:00",
            },
        ),
        event(
            TaskEventType.COMPLETED,
            datetime(2026, 6, 9, 10, tzinfo=timezone.utc),
            {
                "priority": "medium",
                "category_id": None,
                "deadline": "2026-06-08T10:00:00+00:00",
                "completed_at": "2026-06-09T10:00:00+00:00",
            },
        ),
        event(TaskEventType.DELETED, datetime(2026, 6, 10, 10, tzinfo=timezone.utc)),
    ]

    report = aggregate_task_events(
        events,
        date_from=date(2026, 6, 1),
        date_to=date(2026, 6, 14),
        interval=AnalyticsInterval.WEEK,
        category_names={"category-1": "Study"},
    )

    assert report.created_tasks == 1
    assert report.completed_tasks == 2
    assert report.deleted_tasks == 1
    assert report.on_time_completed == 1
    assert report.overdue_completed == 1
    assert report.by_priority == {"high": 1, "medium": 1}
    assert report.by_category == {"Study": 1, "Uncategorized": 1}
    assert [point.period for point in report.trend] == [date(2026, 6, 1), date(2026, 6, 8)]
    assert report.trend[0].created == 1
    assert report.trend[1].completed == 1
