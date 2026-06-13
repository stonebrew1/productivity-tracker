from app.services.group_activity_service import (
    create_activity_comment,
    create_group_update,
    list_group_activity,
    react_to_activity,
)


def test_group_activity_service_exposes_coordination_operations() -> None:
    assert callable(list_group_activity)
    assert callable(create_group_update)
    assert callable(create_activity_comment)
    assert callable(react_to_activity)
