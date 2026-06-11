from datetime import datetime, timezone
from uuid import uuid4

from app.models.task import TaskPriority, TaskStatus
from app.services.task_event_service import build_changes, serialize_event_value


def test_serialize_event_value_supports_domain_values() -> None:
    identifier = uuid4()
    occurred_at = datetime(2026, 6, 10, 12, 30, tzinfo=timezone.utc)

    assert serialize_event_value(identifier) == str(identifier)
    assert serialize_event_value(occurred_at) == "2026-06-10T12:30:00+00:00"
    assert serialize_event_value(TaskPriority.HIGH) == "high"


def test_build_changes_only_includes_modified_fields() -> None:
    changes = build_changes(
        {
            "title": "Draft report",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.MEDIUM,
        },
        {
            "title": "Final report",
            "status": TaskStatus.DONE,
            "priority": TaskPriority.MEDIUM,
        },
    )

    assert changes == {
        "title": {"from": "Draft report", "to": "Final report"},
        "status": {"from": "todo", "to": "done"},
    }
