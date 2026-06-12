from datetime import datetime, timedelta, timezone

from app.services.group_analytics_service import milestone_risk, workload_balance


def test_milestone_risk_is_explainable() -> None:
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)
    assert milestone_risk(100, now - timedelta(days=1), 0, now) == "complete"
    assert milestone_risk(50, None, 0, now) == "unplanned"
    assert milestone_risk(50, now - timedelta(days=1), 0, now) == "overdue"
    assert milestone_risk(50, now + timedelta(days=3), 0, now) == "at_risk"
    assert milestone_risk(80, now + timedelta(days=14), 1, now) == "at_risk"
    assert milestone_risk(80, now + timedelta(days=3), 0, now) == "on_track"


def test_workload_balance_scores_distribution() -> None:
    assert workload_balance([0, 0]) == 100
    assert workload_balance([2, 2]) == 100
    assert workload_balance([4, 2]) == 50
    assert workload_balance([4, 0]) == 0
