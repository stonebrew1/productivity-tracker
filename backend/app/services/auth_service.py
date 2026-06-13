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
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_stats import UserStats
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


async def register(payload: RegisterRequest, db: AsyncSession) -> User:
    existing_user = await db.scalar(select(User).where(User.email == payload.email))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()
    db.add(UserStats(user_id=user.id))
    await db.commit()
    await db.refresh(user)
    return user


@dataclass(frozen=True)
class IssuedSession:
    response: TokenResponse
    refresh_token: str


async def login(payload: LoginRequest, db: AsyncSession) -> IssuedSession:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return await issue_tokens(user, db)


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
