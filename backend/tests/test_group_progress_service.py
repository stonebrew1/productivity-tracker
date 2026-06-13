from datetime import date

from app.services.group_progress_service import contribution_streak


def test_contribution_streak_counts_consecutive_days() -> None:
    assert contribution_streak(
        [date(2026, 6, 13), date(2026, 6, 12), date(2026, 6, 11)],
        date(2026, 6, 13),
    ) == 3


def test_contribution_streak_allows_yesterday_and_stops_at_gap() -> None:
    assert contribution_streak(
        [date(2026, 6, 12), date(2026, 6, 10)],
        date(2026, 6, 13),
    ) == 1
