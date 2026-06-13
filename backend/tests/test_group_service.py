from app.services.group_service import unique_invite_code


def test_group_invite_code_generator_is_async_callable() -> None:
    assert callable(unique_invite_code)
