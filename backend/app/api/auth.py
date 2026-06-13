from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password, hash_refresh_token, verify_password
from app.models.user import User
from app.schemas.auth import (
    EmailVerificationRequest,
    EmailVerificationCodeRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    ResetPasswordCodeRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerificationSessionResponse,
)
from app.schemas.user import AccountDeleteRequest, PasswordChangeRequest, ProfileUpdate, UserRead
from app.services.auth_service import (
    IssuedSession,
    confirm_email,
    confirm_email_code,
    issue_tokens,
    login,
    logout_session,
    refresh_session,
    register,
    request_password_reset,
    reset_password_with_code,
    reset_password_with_token,
    resend_verification,
)


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


@router.post("/register", response_model=RegistrationResponse, status_code=201)
async def register_user(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> RegistrationResponse:
    return await register(payload, db)


@router.post("/verify-email", response_model=VerificationSessionResponse)
async def verify_email(
    payload: EmailVerificationRequest,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: AsyncSession = Depends(get_db),
) -> VerificationSessionResponse:
    token_digest = hash_refresh_token(payload.token)
    user = await db.scalar(select(User).where(User.email_verification_token == token_digest))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link is invalid.")
    was_verified = user.is_email_verified
    confirmation = await confirm_email(payload.token, db)
    if was_verified:
        return VerificationSessionResponse(message=confirmation.message)
    await logout_session(refresh_token, db)
    session = await issue_tokens(user, db)
    set_refresh_cookie(response, session)
    return VerificationSessionResponse(**session.response.model_dump(), message=confirmation.message)


@router.post("/verify-email-code", response_model=VerificationSessionResponse)
async def verify_email_code(
    payload: EmailVerificationCodeRequest,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: AsyncSession = Depends(get_db),
) -> VerificationSessionResponse:
    user = await db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation code is invalid.")
    was_verified = user.is_email_verified
    confirmation = await confirm_email_code(str(payload.email), payload.code, db)
    if was_verified:
        return VerificationSessionResponse(message=confirmation.message)
    await logout_session(refresh_token, db)
    session = await issue_tokens(user, db)
    set_refresh_cookie(response, session)
    return VerificationSessionResponse(**session.response.model_dump(), message=confirmation.message)


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_confirmation(
    payload: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    return await resend_verification(str(payload.email), db)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    return await request_password_reset(str(payload.email), db)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    result = await reset_password_with_token(payload.token, payload.new_password, db)
    response.delete_cookie(settings.refresh_cookie_name, path="/api/auth")
    return result


@router.post("/reset-password-code", response_model=MessageResponse)
async def reset_password_code(
    payload: ResetPasswordCodeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    result = await reset_password_with_code(
        str(payload.email), payload.code, payload.new_password, db
    )
    response.delete_cookie(settings.refresh_cookie_name, path="/api/auth")
    return result


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    session = await login(payload, db)
    await logout_session(refresh_token, db)
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


@router.put("/me", response_model=UserRead)
async def update_me(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        normalized = value.strip() if isinstance(value, str) else value
        setattr(current_user, field, normalized or None)
    await db.commit()
    return current_user


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    extension = allowed_types.get(avatar.content_type or "")
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Avatar must be a JPEG, PNG, or WebP image.",
        )
    content = await avatar.read(2 * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar file is empty.",
        )
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar cannot exceed 2 MB.",
        )
    avatar_dir = Path(settings.upload_dir) / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}-{uuid4().hex}{extension}"
    target = avatar_dir / filename
    target.write_bytes(content)
    delete_local_avatar(current_user.avatar_url)
    current_user.avatar_url = f"/uploads/avatars/{filename}"
    await db.commit()
    return current_user


@router.delete("/me/avatar", response_model=UserRead)
async def remove_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    delete_local_avatar(current_user.avatar_url)
    current_user.avatar_url = None
    await db.commit()
    return current_user


@router.post("/change-password", status_code=204)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a different password.")
    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()


@router.delete("/account", status_code=204)
async def delete_account(
    payload: AccountDeleteRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect.")
    delete_local_avatar(current_user.avatar_url)
    await db.delete(current_user)
    await db.commit()
    response.delete_cookie(settings.refresh_cookie_name, path="/api/auth")


def delete_local_avatar(avatar_url: str | None) -> None:
    prefix = "/uploads/avatars/"
    if not avatar_url or not avatar_url.startswith(prefix):
        return
    filename = Path(avatar_url).name
    target = Path(settings.upload_dir) / "avatars" / filename
    if target.is_file():
        target.unlink()
