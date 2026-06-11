import pytest

from app.core.security import hash_password, verify_password


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_password_hash_rejects_more_than_72_bytes() -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("і" * 37)
