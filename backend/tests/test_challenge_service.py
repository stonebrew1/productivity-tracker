from uuid import UUID

from app.services.challenge_service import challenge_reward_key


def test_challenge_reward_key_is_scoped_to_challenge_and_user() -> None:
    challenge_id = UUID("11111111-1111-1111-1111-111111111111")
    user_id = UUID("22222222-2222-2222-2222-222222222222")

    assert challenge_reward_key(challenge_id, user_id) == (
        "challenge:11111111-1111-1111-1111-111111111111:"
        "22222222-2222-2222-2222-222222222222"
    )
