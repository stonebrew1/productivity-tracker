from datetime import datetime, timezone

from app.services.gamification_service import QUEST_CATALOG, gamification_snapshot, level_from_xp, quest_period


def test_level_progression_uses_fixed_hundred_xp_levels() -> None:
    assert level_from_xp(0) == 1
    assert level_from_xp(99) == 1
    assert level_from_xp(100) == 2
    assert level_from_xp(450) == 5


def test_gamification_snapshot_reports_progress_inside_level() -> None:
    assert gamification_snapshot(245, 6) == {
        "xp_total": 245,
        "level": 3,
        "xp_into_level": 45,
        "xp_for_next_level": 100,
        "current_streak": 6,
    }


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
