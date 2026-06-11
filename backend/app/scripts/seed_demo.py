import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.achievement import Achievement
from app.models.category import Category
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.task_event import TaskEvent, TaskEventType
from app.models.user import User
from app.models.user_stats import UserStats


DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "password123"

TASK_BLUEPRINTS = [
    ("Submit database coursework", "Study", TaskPriority.HIGH, 29, -1),
    ("Review distributed systems notes", "Study", TaskPriority.MEDIUM, 27, 1),
    ("Complete API authentication module", "Work", TaskPriority.HIGH, 25, -2),
    ("Prepare weekly client update", "Work", TaskPriority.MEDIUM, 23, 0),
    ("Run five kilometers", "Health", TaskPriority.MEDIUM, 21, -1),
    ("Read research paper on event sourcing", "Study", TaskPriority.LOW, 19, 2),
    ("Refactor analytics service", "Work", TaskPriority.HIGH, 17, -1),
    ("Book dental appointment", "Personal", TaskPriority.LOW, 16, 3),
    ("Finish React dashboard", "Work", TaskPriority.HIGH, 14, 0),
    ("Practice English presentation", "Study", TaskPriority.MEDIUM, 13, -1),
    ("Complete strength workout", "Health", TaskPriority.MEDIUM, 11, 1),
    ("Write bachelor project introduction", "Study", TaskPriority.HIGH, 10, -2),
    ("Organize monthly expenses", "Personal", TaskPriority.MEDIUM, 8, 0),
    ("Add backend test coverage", "Work", TaskPriority.HIGH, 7, -1),
    ("Prepare architecture diagrams", "Study", TaskPriority.HIGH, 5, 2),
    ("Plan meals for the week", "Health", TaskPriority.LOW, 4, -1),
    ("Update project documentation", "Work", TaskPriority.MEDIUM, 3, 0),
    ("Complete statistics chapter draft", "Study", TaskPriority.HIGH, 2, -1),
]

OPEN_TASKS = [
    ("Prepare project defense slides", "Study", TaskPriority.HIGH, 5, TaskStatus.IN_PROGRESS),
    ("Implement CSV analytics export", "Work", TaskPriority.MEDIUM, 8, TaskStatus.TODO),
    ("Schedule weekly running plan", "Health", TaskPriority.LOW, 4, TaskStatus.TODO),
    ("Renew cloud hosting subscription", "Personal", TaskPriority.MEDIUM, 2, TaskStatus.IN_PROGRESS),
    ("Research notification queues", "Work", TaskPriority.LOW, 10, TaskStatus.TODO),
    ("Outline usability testing plan", "Study", TaskPriority.MEDIUM, 7, TaskStatus.TODO),
]


def event_snapshot(
    status: TaskStatus,
    priority: TaskPriority,
    category_id: str,
    deadline: datetime | None,
    completed_at: datetime | None,
) -> dict:
    return {
        "status": status.value,
        "priority": priority.value,
        "category_id": category_id,
        "deadline": deadline.isoformat() if deadline else None,
        "completed_at": completed_at.isoformat() if completed_at else None,
    }


async def seed_demo() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not user:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            await db.flush()
        else:
            user.password_hash = hash_password(DEMO_PASSWORD)

        await db.execute(delete(Achievement).where(Achievement.user_id == user.id))
        await db.execute(delete(TaskEvent).where(TaskEvent.user_id == user.id))
        await db.execute(delete(Task).where(Task.user_id == user.id))
        await db.execute(delete(Category).where(Category.user_id == user.id))
        await db.execute(delete(UserStats).where(UserStats.user_id == user.id))
        await db.flush()

        categories = {
            name: Category(name=name, user_id=user.id)
            for name in ("Study", "Work", "Health", "Personal")
        }
        db.add_all(categories.values())
        await db.flush()

        completed_tasks: list[Task] = []
        for index, (title, category_name, priority, age_days, timing_days) in enumerate(TASK_BLUEPRINTS):
            created_at = now - timedelta(days=age_days, hours=2 + index % 5)
            deadline = created_at + timedelta(days=3 + index % 4)
            completed_at = min(
                deadline + timedelta(days=timing_days),
                now - timedelta(hours=index + 1),
            )
            category = categories[category_name]
            task = Task(
                title=title,
                description=f"Demo activity for the {category_name.lower()} category.",
                priority=priority,
                status=TaskStatus.DONE,
                deadline=deadline,
                completed_at=completed_at,
                user_id=user.id,
                category_id=category.id,
            )
            db.add(task)
            await db.flush()
            completed_tasks.append(task)

            db.add(
                TaskEvent(
                    event_type=TaskEventType.CREATED,
                    task_id=task.id,
                    task_title=task.title,
                    user_id=user.id,
                    occurred_at=created_at,
                    changes={
                        "title": {"from": None, "to": task.title},
                        "_snapshot": event_snapshot(
                            TaskStatus.TODO,
                            priority,
                            str(category.id),
                            deadline,
                            None,
                        ),
                    },
                )
            )
            db.add(
                TaskEvent(
                    event_type=TaskEventType.COMPLETED,
                    task_id=task.id,
                    task_title=task.title,
                    user_id=user.id,
                    occurred_at=completed_at,
                    changes={
                        "status": {"from": TaskStatus.TODO.value, "to": TaskStatus.DONE.value},
                        "_snapshot": event_snapshot(
                            TaskStatus.DONE,
                            priority,
                            str(category.id),
                            deadline,
                            completed_at,
                        ),
                    },
                )
            )

        for index, (title, category_name, priority, due_in_days, task_status) in enumerate(OPEN_TASKS):
            created_at = now - timedelta(days=6 - index, hours=index)
            deadline = now + timedelta(days=due_in_days)
            category = categories[category_name]
            task = Task(
                title=title,
                description="Upcoming demo task.",
                priority=priority,
                status=task_status,
                deadline=deadline,
                user_id=user.id,
                category_id=category.id,
            )
            db.add(task)
            await db.flush()
            db.add(
                TaskEvent(
                    event_type=TaskEventType.CREATED,
                    task_id=task.id,
                    task_title=task.title,
                    user_id=user.id,
                    occurred_at=created_at,
                    changes={
                        "_snapshot": event_snapshot(
                            TaskStatus.TODO,
                            priority,
                            str(category.id),
                            deadline,
                            None,
                        )
                    },
                )
            )
            if task_status == TaskStatus.IN_PROGRESS:
                db.add(
                    TaskEvent(
                        event_type=TaskEventType.STATUS_CHANGED,
                        task_id=task.id,
                        task_title=task.title,
                        user_id=user.id,
                        occurred_at=created_at + timedelta(hours=8),
                        changes={
                            "status": {
                                "from": TaskStatus.TODO.value,
                                "to": TaskStatus.IN_PROGRESS.value,
                            },
                            "_snapshot": event_snapshot(
                                TaskStatus.IN_PROGRESS,
                                priority,
                                str(category.id),
                                deadline,
                                None,
                            ),
                        },
                    )
                )

        for index, category_name in enumerate(("Work", "Personal", "Study")):
            task_id = uuid4()
            created_at = now - timedelta(days=22 - index * 6)
            deleted_at = created_at + timedelta(days=2)
            category = categories[category_name]
            snapshot = event_snapshot(
                TaskStatus.TODO,
                TaskPriority.LOW,
                str(category.id),
                created_at + timedelta(days=5),
                None,
            )
            db.add_all(
                [
                    TaskEvent(
                        event_type=TaskEventType.CREATED,
                        task_id=task_id,
                        task_title=f"Archived {category_name.lower()} idea",
                        user_id=user.id,
                        occurred_at=created_at,
                        changes={"_snapshot": snapshot},
                    ),
                    TaskEvent(
                        event_type=TaskEventType.DELETED,
                        task_id=task_id,
                        task_title=f"Archived {category_name.lower()} idea",
                        user_id=user.id,
                        occurred_at=deleted_at,
                        changes={"snapshot": snapshot, "_snapshot": snapshot},
                    ),
                ]
            )

        db.add_all(
            [
                Achievement(
                    title="First win",
                    description="Completed the first tracked task.",
                    awarded_at=completed_tasks[0].completed_at,
                    user_id=user.id,
                    task_id=completed_tasks[0].id,
                ),
                Achievement(
                    title="Deadline keeper",
                    description="Completed ten tasks on time.",
                    awarded_at=completed_tasks[12].completed_at,
                    user_id=user.id,
                    task_id=completed_tasks[12].id,
                ),
                Achievement(
                    title="Productivity sprint",
                    description="Completed five tasks in one week.",
                    awarded_at=completed_tasks[-1].completed_at,
                    user_id=user.id,
                    task_id=completed_tasks[-1].id,
                ),
            ]
        )
        db.add(
            UserStats(
                total_tasks=len(TASK_BLUEPRINTS) + len(OPEN_TASKS),
                completed_tasks=len(TASK_BLUEPRINTS),
                current_streak=4,
                user_id=user.id,
            )
        )
        await db.commit()

    print(
        f"Seeded {DEMO_EMAIL}: {len(TASK_BLUEPRINTS)} completed tasks, "
        f"{len(OPEN_TASKS)} active tasks, 3 deleted-task histories, and 3 achievements."
    )


if __name__ == "__main__":
    asyncio.run(seed_demo())
