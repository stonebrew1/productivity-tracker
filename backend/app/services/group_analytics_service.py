from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember, GroupMilestone, GroupTask
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.group import (
    GroupAnalyticsRead,
    GroupMilestoneRisk,
    GroupVelocityPoint,
    GroupWorkloadEntry,
)
from app.services.group_task_service import require_membership


def milestone_risk(
    progress_percent: int,
    target_date: datetime | None,
    urgent_linked_tasks: int,
    now: datetime,
) -> str:
    if progress_percent == 100:
        return "complete"
    if not target_date:
        return "unplanned"
    if target_date < now:
        return "overdue"
    if urgent_linked_tasks or (
        target_date <= now + timedelta(days=7) and progress_percent < 75
    ):
        return "at_risk"
    return "on_track"


def workload_balance(active_counts: Iterable[int]) -> int:
    counts = list(active_counts)
    if not counts or max(counts) == 0:
        return 100
    return max(0, round((1 - (max(counts) - min(counts)) / max(counts)) * 100))


async def group_analytics(
    group_id: UUID, viewer_id: UUID, db: AsyncSession
) -> GroupAnalyticsRead:
    await require_membership(group_id, viewer_id, db)
    now = datetime.now(timezone.utc)
    start_date = now.date() - timedelta(days=13)
    memberships = list(
        await db.scalars(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at.asc())
        )
    )
    users = {
        user.id: user
        for user in list(
            await db.scalars(select(User).where(User.id.in_([item.user_id for item in memberships])))
        )
    }
    tasks = list(await db.scalars(select(GroupTask).where(GroupTask.group_id == group_id)))
    milestones = list(
        await db.scalars(
            select(GroupMilestone)
            .where(GroupMilestone.group_id == group_id)
            .order_by(GroupMilestone.target_date.asc().nulls_last())
        )
    )

    active_by_user: dict[UUID, int] = defaultdict(int)
    completed_by_user: dict[UUID, int] = defaultdict(int)
    overdue_by_user: dict[UUID, int] = defaultdict(int)
    velocity_by_date = {
        start_date + timedelta(days=offset): 0 for offset in range(14)
    }
    cycle_hours = []
    completed_tasks = 0
    overdue_tasks = 0
    due_soon_tasks = 0
    for task in tasks:
        if task.status == TaskStatus.DONE:
            completed_tasks += 1
            completed_by_user[task.assigned_to_id] += 1
            if task.completed_at:
                if task.completed_at.date() in velocity_by_date:
                    velocity_by_date[task.completed_at.date()] += 1
                cycle_hours.append((task.completed_at - task.created_at).total_seconds() / 3600)
            continue
        active_by_user[task.assigned_to_id] += 1
        if task.deadline and task.deadline < now:
            overdue_tasks += 1
            overdue_by_user[task.assigned_to_id] += 1
        elif task.deadline and task.deadline <= now + timedelta(days=7):
            due_soon_tasks += 1

    workload = []
    for membership in memberships:
        user = users[membership.user_id]
        workload.append(
            GroupWorkloadEntry(
                user_id=user.id,
                display_name=user.display_name or user.email.split("@")[0],
                active_tasks=active_by_user[user.id],
                completed_tasks=completed_by_user[user.id],
                overdue_tasks=overdue_by_user[user.id],
            )
        )

    risks = []
    for milestone in milestones:
        linked = [task for task in tasks if task.milestone_id == milestone.id]
        done = sum(task.status == TaskStatus.DONE for task in linked)
        progress = round((done / len(linked)) * 100) if linked else 0
        urgent_linked = sum(
            task.status != TaskStatus.DONE
            and task.deadline is not None
            and task.deadline <= now + timedelta(days=7)
            for task in linked
        )
        risks.append(
            GroupMilestoneRisk(
                milestone_id=milestone.id,
                title=milestone.title,
                progress_percent=progress,
                target_date=milestone.target_date,
                risk=milestone_risk(progress, milestone.target_date, urgent_linked, now),
            )
        )

    total_tasks = len(tasks)
    return GroupAnalyticsRead(
        total_tasks=total_tasks,
        completion_rate=round((completed_tasks / total_tasks) * 100) if total_tasks else 0,
        active_tasks=total_tasks - completed_tasks,
        overdue_tasks=overdue_tasks,
        due_soon_tasks=due_soon_tasks,
        average_cycle_days=round(sum(cycle_hours) / len(cycle_hours) / 24, 1) if cycle_hours else 0,
        workload_balance_score=workload_balance(item.active_tasks for item in workload),
        velocity=[
            GroupVelocityPoint(
                date=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                completed=count,
            )
            for day, count in velocity_by_date.items()
        ],
        workload=workload,
        milestone_risks=risks,
    )
