import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_registration_accepts_name_and_strong_password() -> None:
    payload = RegisterRequest(
        display_name="Ada Lovelace",
        email="ada@example.com",
        password="FocusedWork9",
    )

    assert payload.display_name == "Ada Lovelace"


@pytest.mark.parametrize(
    "password",
    ["shortA1", "alllowercase1", "ALLUPPERCASE1", "NoNumbersHere"],
)
def test_registration_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            display_name="Ada Lovelace",
            email="ada@example.com",
            password=password,
        )
