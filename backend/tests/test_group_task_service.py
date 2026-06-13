from app.services.group_task_service import create_group_task, list_group_tasks, update_group_task


def test_group_task_service_exposes_collaboration_operations() -> None:
    assert callable(create_group_task)
    assert callable(list_group_tasks)
    assert callable(update_group_task)
