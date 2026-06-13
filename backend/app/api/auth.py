from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.core.config import get_settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import IssuedSession, login, logout_session, refresh_session, register


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_refresh_cookie(response: Response, session: IssuedSession) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=session.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path="/api/auth",
    )


@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    return await register(payload, db)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    session = await login(payload, db)
    set_refresh_cookie(response, session)
    return session.response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session not found.")
    session = await refresh_session(refresh_token, db)
    set_refresh_cookie(response, session)
    return session.response


@router.post("/logout", status_code=204)
async def logout_user(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: AsyncSession = Depends(get_db),
) -> None:
    await logout_session(refresh_token, db)
    response.delete_cookie(settings.refresh_cookie_name, path="/api/auth")


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
