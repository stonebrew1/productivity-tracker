from datetime import datetime
from uuid import UUID

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.auth import validate_bcrypt_password


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    is_email_verified: bool
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    bio: str | None = Field(default=None, max_length=500)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Name must contain at least 2 characters.")
        return normalized


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(max_length=72)
    new_password: str = Field(min_length=10, max_length=72)

    _validate_current_password = field_validator("current_password")(validate_bcrypt_password)
    _validate_new_password = field_validator("new_password")(validate_bcrypt_password)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must include a lowercase letter.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must include an uppercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must include a number.")
        return value


class AccountDeleteRequest(BaseModel):
    password: str = Field(max_length=72)
    confirmation: str

    _validate_password = field_validator("password")(validate_bcrypt_password)

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, value: str) -> str:
        if value != "DELETE":
            raise ValueError("Type DELETE to confirm account deletion.")
        return value
