import pytest
from pydantic import ValidationError

from app.schemas.auth import EmailVerificationCodeRequest, RegisterRequest


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


def test_email_verification_code_accepts_six_digits() -> None:
    payload = EmailVerificationCodeRequest(email="ada@example.com", code="012345")

    assert payload.code == "012345"


@pytest.mark.parametrize("code", ["12345", "1234567", "12A456"])
def test_email_verification_code_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(ValidationError):
        EmailVerificationCodeRequest(email="ada@example.com", code=code)
