import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_bcrypt_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")
    return password


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=10, max_length=72)

    _validate_password = field_validator("password")(validate_bcrypt_password)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Name must contain at least 2 characters.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must include a lowercase letter.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must include an uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must include a number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)

    _validate_password = field_validator("password")(validate_bcrypt_password)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class VerificationSessionResponse(BaseModel):
    message: str
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


class RegistrationResponse(BaseModel):
    message: str
    email: EmailStr
    verification_url: str | None = None


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)


class EmailVerificationCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
    verification_url: str | None = None
