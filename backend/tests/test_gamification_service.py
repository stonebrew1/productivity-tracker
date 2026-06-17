from datetime import datetime, timezone

from app.core.gamification import calculate_task_xp, xp_required_for_level
from app.models.task import TaskPriority
from app.services.gamification_service import QUEST_CATALOG, gamification_snapshot, level_from_xp, quest_period


def test_level_progression_requires_more_xp_for_each_level() -> None:
    assert level_from_xp(0) == 1
    assert level_from_xp(99) == 1
    assert level_from_xp(100) == 2
    assert level_from_xp(249) == 2
    assert level_from_xp(250) == 3
    assert level_from_xp(450) == 4
    assert xp_required_for_level(1) == 100
    assert xp_required_for_level(2) == 150
    assert xp_required_for_level(5) == 300


def test_gamification_snapshot_reports_progress_inside_level() -> None:
    assert gamification_snapshot(245, 6) == {
        "xp_total": 245,
        "level": 2,
        "xp_into_level": 145,
        "xp_for_next_level": 150,
        "current_streak": 6,
    }


def test_task_xp_increases_with_priority_and_effort() -> None:
    assert calculate_task_xp(TaskPriority.LOW, 15) == 10
    assert calculate_task_xp(TaskPriority.MEDIUM, 30) == 20
    assert calculate_task_xp(TaskPriority.HIGH, 60) == 30
    assert calculate_task_xp(TaskPriority.HIGH, 120) == 40
    assert calculate_task_xp(TaskPriority.HIGH, 300) == 60


def test_task_without_estimate_uses_thirty_minute_default() -> None:
    assert calculate_task_xp(TaskPriority.MEDIUM, None) == 20


def test_quest_periods_expire_at_next_day_or_week() -> None:
    current = datetime(2026, 6, 11, 14, tzinfo=timezone.utc)

    daily_start, daily_end = quest_period("daily", current)
    weekly_start, weekly_end = quest_period("weekly", current)

    assert daily_start.isoformat() == "2026-06-11T00:00:00+00:00"
    assert daily_end.isoformat() == "2026-06-12T00:00:00+00:00"
    assert weekly_start.isoformat() == "2026-06-08T00:00:00+00:00"
    assert weekly_end.isoformat() == "2026-06-15T00:00:00+00:00"


def test_social_encouragement_quest_is_part_of_catalog() -> None:
    quest = next(item for item in QUEST_CATALOG if item["code"] == "weekly_encourage_3")

    assert quest["metric"] == "reactions"
    assert quest["target"] == 3


def test_social_comment_quest_is_part_of_catalog() -> None:
    quest = next(item for item in QUEST_CATALOG if item["code"] == "weekly_comment_2")

    assert quest["metric"] == "comments"
    assert quest["target"] == 2
