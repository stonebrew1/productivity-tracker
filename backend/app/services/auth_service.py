from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.services.email_service import send_verification_email
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_stats import UserStats
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegistrationResponse,
    TokenResponse,
)


def verification_url(token: str) -> str:
    return f"{get_settings().frontend_origin.rstrip('/')}/verify-email?token={token}"


def issue_email_verification(user: User) -> tuple[str, str]:
    settings = get_settings()
    raw_token = create_refresh_token()
    user.email_verification_token = hash_refresh_token(raw_token)
    user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.email_verification_expire_hours
    )
    return raw_token, verification_url(raw_token)


async def register(payload: RegisterRequest, db: AsyncSession) -> RegistrationResponse:
    email = str(payload.email).lower()
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_email_verified=False,
    )
    db.add(user)
    await db.flush()
    db.add(UserStats(user_id=user.id))
    _, url = issue_email_verification(user)
    await db.commit()
    await send_verification_email(user.email, user.display_name, url)
    settings = get_settings()
    return RegistrationResponse(
        message="Account created. Check your email to confirm your account.",
        email=user.email,
        verification_url=url if settings.email_delivery_mode == "console" else None,
    )


@dataclass(frozen=True)
class IssuedSession:
    response: TokenResponse
    refresh_token: str


async def login(payload: LoginRequest, db: AsyncSession) -> IssuedSession:
    user = await db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirm your email before signing in.",
        )
    return await issue_tokens(user, db)


async def confirm_email(token: str, db: AsyncSession) -> MessageResponse:
    token_digest = hash_refresh_token(token)
    user = await db.scalar(
        select(User).where(User.email_verification_token == token_digest)
    )
    now = datetime.now(timezone.utc)
    if (
        not user
        or not user.email_verification_expires_at
        or user.email_verification_expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired.",
        )
    user.is_email_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None
    await db.commit()
    return MessageResponse(message="Email confirmed. You can now sign in.")


async def resend_verification(email: str, db: AsyncSession) -> MessageResponse:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    generic_message = "If the account exists and is not confirmed, a new email has been sent."
    if not user or user.is_email_verified:
        return MessageResponse(message=generic_message)
    _, url = issue_email_verification(user)
    await db.commit()
    await send_verification_email(user.email, user.display_name or user.email.split("@")[0], url)
    return MessageResponse(
        message=generic_message,
        verification_url=url if get_settings().email_delivery_mode == "console" else None,
    )


async def issue_tokens(
    user: User, db: AsyncSession, family_id: UUID | None = None
) -> IssuedSession:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    raw_refresh_token = create_refresh_token()
    refresh_token = RefreshToken(
        token=hash_refresh_token(raw_refresh_token),
        created_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        family_id=family_id or uuid4(),
        user_id=user.id,
    )
    db.add(refresh_token)
    await db.commit()
    return IssuedSession(
        response=TokenResponse(
            access_token=create_access_token(user.id, user.role.value),
            expires_in=settings.access_token_expire_minutes * 60,
        ),
        refresh_token=raw_refresh_token,
    )


async def revoke_token_family(family_id: UUID, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    tokens = list(
        await db.scalars(select(RefreshToken).where(RefreshToken.family_id == family_id))
    )
    for token in tokens:
        if not token.revoked_at:
            token.revoked_at = now


async def refresh_session(token: str, db: AsyncSession) -> IssuedSession:
    token_digest = hash_refresh_token(token)
    refresh_token = await db.scalar(
        select(RefreshToken).where(
            (RefreshToken.token == token_digest) | (RefreshToken.token == token)
        )
    )
    now = datetime.now(timezone.utc)
    if not refresh_token or refresh_token.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    if refresh_token.revoked_at:
        await revoke_token_family(refresh_token.family_id, db)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected.")
    user = await db.get(User, refresh_token.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    refresh_token.revoked_at = now
    issued = await issue_tokens(user, db, refresh_token.family_id)
    refresh_token.replaced_by_token = hash_refresh_token(issued.refresh_token)
    await db.commit()
    return issued


async def logout_session(token: str | None, db: AsyncSession) -> None:
    if not token:
        return
    token_digest = hash_refresh_token(token)
    refresh_token = await db.scalar(
        select(RefreshToken).where(
            (RefreshToken.token == token_digest) | (RefreshToken.token == token)
        )
    )
    if refresh_token:
        await revoke_token_family(refresh_token.family_id, db)
        await db.commit()
