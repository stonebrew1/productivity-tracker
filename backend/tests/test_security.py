from uuid import uuid4

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_password_hash_rejects_more_than_72_bytes() -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("a" * 73)


def test_access_token_has_expected_identity_and_type() -> None:
    user_id = uuid4()
    payload = decode_access_token(create_access_token(user_id, "user"))

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "user"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_refresh_tokens_are_random_and_stored_as_digests() -> None:
    first = create_refresh_token()
    second = create_refresh_token()

    assert first != second
    assert hash_refresh_token(first) != first
    assert hash_refresh_token(first) == hash_refresh_token(first)
