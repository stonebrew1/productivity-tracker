from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_bcrypt_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")
    return password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    _validate_password = field_validator("password")(validate_bcrypt_password)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)

    _validate_password = field_validator("password")(validate_bcrypt_password)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
