from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from database import get_session
from services.user_service import UserService
from services.token_service import TokenService
from schemas.user import (
    UserCreate,
    UserProfileResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
)

from schemas.token import (
    Token,
    RefreshTokenRequest,
    RefreshTokenResponse,
    LogoutResponse,
    LogoutRequest
)

from models.user import User
from api.v1.deps import get_current_active_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED)
async def register_user(
        *,
        db: AsyncSession = Depends(get_session),
        user_in: UserCreate
) -> Any:
    """
    Register a new user
    """
    user_service = UserService(db)
    user = await user_service.register_user(
        username=user_in.username,
        email=user_in.email,
        password=user_in.password,
        fullname=user_in.fullname,
        country=user_in.country
    )
    user.id = str(user.id)  # Convert UUID to string for response
    return user


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
        request: RefreshTokenRequest,
        db: AsyncSession = Depends(get_session)
):
    """
    Refresh access token using a valid refresh token.
    """
    token_service = TokenService(db)
    token_data = await token_service.refresh_tokens(request.refresh_token)

    return token_data


@router.post("/login", response_model=Token)
async def login(
        db: AsyncSession = Depends(get_session),
        form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Authenticate user and return access token
    """
    user_service = UserService(db)
    user = await user_service.authenticate_user(
        username_or_email=form_data.username,
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_service = TokenService(db)
    access_tokens = await token_service.create_tokens(str(user.id))

    return access_tokens


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
        *,
        db: AsyncSession = Depends(get_session),
        password_in: ChangePasswordRequest = Body(...),
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Change password for the authenticated user
    """
    user_service = UserService(db)
    result = await user_service.change_password(
        user_id=str(current_user.id),
        current_password=password_in.current_password,
        new_password=password_in.new_password
    )
    return {"success": result}


@router.post("/logout", response_model=LogoutResponse)
async def logout(
        db: AsyncSession = Depends(get_session),
        request: LogoutRequest = Body(...),
        current_user: Dict = Depends(get_current_active_user)  # Ensure user is authenticated
):
    """
    Logs the user out by revoking their refresh token.
    """

    token_service = TokenService(db)
    refresh_token = request.refresh_token

    revoked = await token_service.revoke_refresh_token(refresh_token, reason="User logout")

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already revoked refresh token"
        )

    return {
        "success": True,
        "message": "Logged out successfully"
    }
