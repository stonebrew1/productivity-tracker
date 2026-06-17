from collections.abc import Mapping

from app.models.task import TaskPriority


DEFAULT_TASK_XP_RULE: dict = {
    "base_xp": 10,
    "default_minutes": 30,
    "priority_bonus": {
        TaskPriority.LOW.value: 0,
        TaskPriority.MEDIUM.value: 5,
        TaskPriority.HIGH.value: 10,
    },
    "effort_bonus": [
        {"up_to_minutes": 15, "xp": 0},
        {"up_to_minutes": 30, "xp": 5},
        {"up_to_minutes": 60, "xp": 10},
        {"up_to_minutes": 120, "xp": 20},
        {"up_to_minutes": 240, "xp": 30},
        {"up_to_minutes": None, "xp": 40},
    ],
}


def calculate_task_xp(
    priority: TaskPriority | str,
    estimated_minutes: int | None,
    rule: Mapping | None = None,
) -> int:
    active_rule = {**DEFAULT_TASK_XP_RULE, **(rule or {})}
    priority_value = priority.value if isinstance(priority, TaskPriority) else priority
    minutes = estimated_minutes or int(active_rule["default_minutes"])
    priority_bonus = int(active_rule["priority_bonus"].get(priority_value, 0))
    effort_bonus = 0
    for band in active_rule["effort_bonus"]:
        limit = band["up_to_minutes"]
        if limit is None or minutes <= int(limit):
            effort_bonus = int(band["xp"])
            break
    return int(active_rule["base_xp"]) + priority_bonus + effort_bonus


def xp_required_for_level(level: int, base_xp: int = 100, growth_xp: int = 50) -> int:
    return base_xp + max(0, level - 1) * growth_xp


def level_progress_from_xp(
    xp_total: int,
    base_xp: int = 100,
    growth_xp: int = 50,
) -> tuple[int, int, int]:
    level = 1
    remaining = max(0, xp_total)
    required = xp_required_for_level(level, base_xp, growth_xp)
    while remaining >= required:
        remaining -= required
        level += 1
        required = xp_required_for_level(level, base_xp, growth_xp)
    return level, remaining, required
