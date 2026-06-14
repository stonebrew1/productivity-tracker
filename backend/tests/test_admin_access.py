import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_admin
from app.models.user import User, UserRole


def user_with_role(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value}@example.com",
        password_hash="unused",
        role=role,
        is_email_verified=True,
    )


def test_admin_dependency_accepts_administrator() -> None:
    admin = user_with_role(UserRole.ADMIN)

    assert asyncio.run(get_current_admin(admin)) is admin


def test_admin_dependency_rejects_regular_user() -> None:
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_admin(user_with_role(UserRole.USER)))

    assert error.value.status_code == 403
