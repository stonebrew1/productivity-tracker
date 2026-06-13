from app.services.group_milestone_service import create_milestone, list_milestones


def test_group_milestone_service_exposes_progress_operations() -> None:
    assert callable(create_milestone)
    assert callable(list_milestones)
