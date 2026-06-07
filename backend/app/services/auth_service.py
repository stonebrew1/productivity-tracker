from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
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


async def login(payload: LoginRequest, db: AsyncSession) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return await issue_tokens(user, db)


async def issue_tokens(user: User, db: AsyncSession) -> TokenResponse:
    settings = get_settings()
    refresh_token = RefreshToken(
        token=token_urlsafe(48),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        user_id=user.id,
    )
    db.add(refresh_token)
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=refresh_token.token,
    )


async def refresh_session(token: str, db: AsyncSession) -> TokenResponse:
    refresh_token = await db.scalar(select(RefreshToken).where(RefreshToken.token == token))
    if not refresh_token or refresh_token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    user = await db.get(User, refresh_token.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    await db.delete(refresh_token)
    return await issue_tokens(user, db)
