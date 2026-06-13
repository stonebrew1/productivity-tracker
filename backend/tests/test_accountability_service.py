from uuid import UUID

from app.services.accountability_service import accountability_reward_key


def test_accountability_reward_keys_are_role_specific() -> None:
    commitment_id = UUID("11111111-1111-1111-1111-111111111111")

    owner_key = accountability_reward_key(commitment_id, "owner")
    partner_key = accountability_reward_key(commitment_id, "partner")

    assert owner_key != partner_key
    assert owner_key.endswith(":owner")
    assert partner_key.endswith(":partner")
