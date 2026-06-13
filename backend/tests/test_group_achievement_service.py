from app.services.group_achievement_service import (
    GROUP_ACHIEVEMENTS,
    achievement_metrics,
    list_group_achievements,
)


def test_group_achievement_catalog_has_unique_codes_and_valid_targets() -> None:
    codes = [item.code for item in GROUP_ACHIEVEMENTS]

    assert len(codes) == len(set(codes))
    assert all(item.target > 0 for item in GROUP_ACHIEVEMENTS)
    assert all(item.reward_xp > 0 for item in GROUP_ACHIEVEMENTS)


def test_group_achievement_service_exposes_progress_operations() -> None:
    assert callable(achievement_metrics)
    assert callable(list_group_achievements)
