from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.task_event import TaskEvent, TaskEventType


ANALYTICS_SNAPSHOT_FIELDS = {
    "status",
    "priority",
    "category_id",
    "deadline",
    "scheduled_for",
    "estimated_minutes",
    "is_focus",
    "completed_at",
}


def serialize_event_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (UUID, Enum)):
        return str(value)
    return value


def build_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for field in after:
        old_value = serialize_event_value(before.get(field))
        new_value = serialize_event_value(after[field])
        if old_value != new_value:
            changes[field] = {"from": old_value, "to": new_value}
    return changes


def task_snapshot(task: Task, fields: set[str]) -> dict[str, Any]:
    return {field: getattr(task, field) for field in fields}


async def record_task_event(
    db: AsyncSession,
    task: Task,
    event_type: TaskEventType,
    changes: dict | None = None,
) -> TaskEvent:
    event_changes = dict(changes or {})
    event_changes["_snapshot"] = {
        field: serialize_event_value(value)
        for field, value in task_snapshot(task, ANALYTICS_SNAPSHOT_FIELDS).items()
    }
    event = TaskEvent(
        event_type=event_type,
        task_id=task.id,
        task_title=task.title,
        changes=event_changes,
        user_id=task.user_id,
    )
    db.add(event)
    await db.flush()
    return event
