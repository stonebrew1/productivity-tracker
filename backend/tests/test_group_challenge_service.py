from app.services.group_challenge_service import (
    challenge_progress,
    create_group_challenge,
    list_group_challenges,
)


def test_group_challenge_service_exposes_team_challenge_operations() -> None:
    assert callable(challenge_progress)
    assert callable(create_group_challenge)
    assert callable(list_group_challenges)
