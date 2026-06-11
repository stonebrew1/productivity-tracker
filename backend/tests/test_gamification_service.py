from app.services.gamification_service import XP_PER_LEVEL, gamification_snapshot, level_from_xp


def test_level_progression_uses_fixed_hundred_xp_levels() -> None:
    assert level_from_xp(0) == 1
    assert level_from_xp(XP_PER_LEVEL - 1) == 1
    assert level_from_xp(XP_PER_LEVEL) == 2
    assert level_from_xp(450) == 5


def test_gamification_snapshot_reports_progress_inside_level() -> None:
    assert gamification_snapshot(245, 6) == {
        "xp_total": 245,
        "level": 3,
        "xp_into_level": 45,
        "xp_for_next_level": 100,
        "current_streak": 6,
    }
