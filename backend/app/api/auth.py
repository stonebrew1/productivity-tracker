from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import login, refresh_session, register


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    return await register(payload, db)


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await login(payload, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await refresh_session(payload.refresh_token, db)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
