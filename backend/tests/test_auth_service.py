import asyncio
from datetime import datetime, timedelta, timezone

from app.core.security import hash_refresh_token
from app.models.user import User
from app.services.auth_service import confirm_email, confirm_email_code


class FakeSession:
    def __init__(self, user: User) -> None:
        self.user = user
        self.commits = 0

    async def scalar(self, _query: object) -> User:
        return self.user

    async def commit(self) -> None:
        self.commits += 1


def verified_user(token: str, code: str) -> User:
    return User(
        email="verified@example.com",
        password_hash="unused",
        is_email_verified=True,
        email_verification_token=hash_refresh_token(token),
        email_verification_code=hash_refresh_token(code),
        email_verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def test_repeated_magic_link_reports_already_confirmed() -> None:
    token = "verification-token"
    db = FakeSession(verified_user(token, "123456"))

    result = asyncio.run(confirm_email(token, db))

    assert result.message == "Email is already confirmed. You can sign in."
    assert db.commits == 0


def test_repeated_confirmation_code_reports_already_confirmed() -> None:
    code = "123456"
    db = FakeSession(verified_user("verification-token", code))

    result = asyncio.run(confirm_email_code("verified@example.com", code, db))

    assert result.message == "Email is already confirmed. You can sign in."
    assert db.commits == 0
