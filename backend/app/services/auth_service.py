from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import randbelow
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
from app.models.password_reset import PasswordReset
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
from app.services.email_service import send_password_reset_email, send_verification_email


def verification_url(token: str) -> str:
    return f"{get_settings().frontend_origin.rstrip('/')}/verify-email?token={token}"


def password_reset_url(token: str) -> str:
    return f"{get_settings().frontend_origin.rstrip('/')}/reset-password?token={token}"


def issue_email_verification(user: User) -> tuple[str, str, str]:
    settings = get_settings()
    raw_token = create_refresh_token()
    code = f"{randbelow(1_000_000):06d}"
    user.email_verification_token = hash_refresh_token(raw_token)
    user.email_verification_code = hash_refresh_token(code)
    user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.email_verification_expire_hours
    )
    return raw_token, verification_url(raw_token), code


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
    _, url, code = issue_email_verification(user)
    try:
        await send_verification_email(user.email, user.display_name, url, code)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send confirmation email. Try again shortly.",
        ) from exc
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
    if user.is_email_verified:
        return MessageResponse(message="Email is already confirmed. You can sign in.")
    user.is_email_verified = True
    await db.commit()
    return MessageResponse(message="Email confirmed. You can now sign in.")


async def confirm_email_code(email: str, code: str, db: AsyncSession) -> MessageResponse:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    now = datetime.now(timezone.utc)
    if (
        not user
        or not user.email_verification_code
        or not user.email_verification_expires_at
        or user.email_verification_expires_at <= now
        or user.email_verification_code != hash_refresh_token(code)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code is invalid or expired.",
        )
    if user.is_email_verified:
        return MessageResponse(message="Email is already confirmed. You can sign in.")
    user.is_email_verified = True
    await db.commit()
    return MessageResponse(message="Email confirmed. You can now sign in.")


async def resend_verification(email: str, db: AsyncSession) -> MessageResponse:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    generic_message = "If the account exists and is not confirmed, a new email has been sent."
    if not user or user.is_email_verified:
        return MessageResponse(message=generic_message)
    _, url, code = issue_email_verification(user)
    try:
        await send_verification_email(
            user.email, user.display_name or user.email.split("@")[0], url, code
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send confirmation email. Try again shortly.",
        ) from exc
    return MessageResponse(
        message=generic_message,
        verification_url=url if get_settings().email_delivery_mode == "console" else None,
    )


async def request_password_reset(email: str, db: AsyncSession) -> MessageResponse:
    generic_message = "If an account exists for that email, reset instructions have been sent."
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if not user or not user.is_email_verified:
        return MessageResponse(message=generic_message)

    now = datetime.now(timezone.utc)
    active_resets = list(
        await db.scalars(
            select(PasswordReset).where(
                PasswordReset.user_id == user.id,
                PasswordReset.used_at.is_(None),
            )
        )
    )
    for reset in active_resets:
        reset.used_at = now

    raw_token = create_refresh_token()
    code = f"{randbelow(1_000_000):06d}"
    db.add(
        PasswordReset(
            token=hash_refresh_token(raw_token),
            code=hash_refresh_token(code),
            expires_at=now + timedelta(minutes=get_settings().password_reset_expire_minutes),
            created_at=now,
            user_id=user.id,
        )
    )
    url = password_reset_url(raw_token)
    try:
        await send_password_reset_email(
            user.email, user.display_name or user.email.split("@")[0], url, code
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send password reset email. Try again shortly.",
        ) from exc
    return MessageResponse(
        message=generic_message,
        verification_url=url if get_settings().email_delivery_mode == "console" else None,
    )


async def reset_password_with_token(
    token: str, new_password: str, db: AsyncSession
) -> MessageResponse:
    reset = await db.scalar(
        select(PasswordReset).where(
            PasswordReset.token == hash_refresh_token(token),
            PasswordReset.used_at.is_(None),
        )
    )
    return await complete_password_reset(reset, new_password, db)


async def reset_password_with_code(
    email: str, code: str, new_password: str, db: AsyncSession
) -> MessageResponse:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    reset = None
    if user:
        reset = await db.scalar(
            select(PasswordReset)
            .where(
                PasswordReset.user_id == user.id,
                PasswordReset.code == hash_refresh_token(code),
                PasswordReset.used_at.is_(None),
            )
            .order_by(PasswordReset.created_at.desc())
        )
    return await complete_password_reset(reset, new_password, db)


async def complete_password_reset(
    reset: PasswordReset | None, new_password: str, db: AsyncSession
) -> MessageResponse:
    now = datetime.now(timezone.utc)
    if not reset or reset.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is invalid or expired.",
        )
    user = await db.get(User, reset.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is invalid or expired.",
        )
    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a password you have not just used.",
        )

    user.password_hash = hash_password(new_password)
    reset.used_at = now
    other_resets = list(
        await db.scalars(
            select(PasswordReset).where(
                PasswordReset.user_id == user.id,
                PasswordReset.used_at.is_(None),
            )
        )
    )
    for other_reset in other_resets:
        other_reset.used_at = now
    active_tokens = list(
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    )
    for active_token in active_tokens:
        active_token.revoked_at = now
    await db.commit()
    return MessageResponse(message="Password reset. Sign in with your new password.")


async def issue_tokens(
    user: User,
    db: AsyncSession,
    family_id: UUID | None = None,
    revoke_existing: bool = True,
) -> IssuedSession:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    active_family_id = family_id or uuid4()
    if revoke_existing:
        existing_tokens = list(
            await db.scalars(
                select(RefreshToken).where(
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        )
        for existing_token in existing_tokens:
            existing_token.revoked_at = now
    raw_refresh_token = create_refresh_token()
    refresh_token = RefreshToken(
        token=hash_refresh_token(raw_refresh_token),
        created_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        family_id=active_family_id,
        user_id=user.id,
    )
    db.add(refresh_token)
    await db.commit()
    return IssuedSession(
        response=TokenResponse(
            access_token=create_access_token(user.id, user.role.value, active_family_id),
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
    issued = await issue_tokens(
        user, db, refresh_token.family_id, revoke_existing=False
    )
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
