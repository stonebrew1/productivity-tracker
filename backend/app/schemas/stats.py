from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class StatsRead(BaseModel):
    total_tasks: int
    completed_tasks: int
    current_streak: int
    completion_rate: float
    by_priority: dict[str, int]
    by_status: dict[str, int]


class AnalyticsInterval(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TrendPoint(BaseModel):
    period: date
    created: int
    completed: int
    deleted: int


class AnalyticsReport(BaseModel):
    date_from: date
    date_to: date
    interval: AnalyticsInterval
    created_tasks: int
    completed_tasks: int
    deleted_tasks: int
    on_time_completed: int
    overdue_completed: int
    without_deadline_completed: int
    by_priority: dict[str, int]
    by_category: dict[str, int]
    trend: list[TrendPoint]
