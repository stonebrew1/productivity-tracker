from pydantic import BaseModel


class StatsRead(BaseModel):
    total_tasks: int
    completed_tasks: int
    current_streak: int
    completion_rate: float
    by_priority: dict[str, int]
    by_status: dict[str, int]
