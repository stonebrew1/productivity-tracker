from datetime import date

from app.services.stats_service import calculate_current_streak


def test_current_streak_counts_consecutive_days_from_today_or_yesterday() -> None:
    today = date(2026, 6, 11)

    assert calculate_current_streak(
        [date(2026, 6, 11), date(2026, 6, 10), date(2026, 6, 9), date(2026, 6, 7)],
        today,
    ) == 3
    assert calculate_current_streak([date(2026, 6, 10), date(2026, 6, 9)], today) == 2
    assert calculate_current_streak([date(2026, 6, 8)], today) == 0
