from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from database import get_session
from services.user_service import UserService
from core.security import create_access_token
from core.config import settings
from schemas.user import (
    UserCreate,
    Token,
    ChangePasswordRequest
)
from models.user import User
from api.v1.deps import get_current_active_user

router = APIRouter()


@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
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
    )
    return {"user": user}


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

    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/user/change-password", response_model=Dict[str, bool])
async def change_password(
        *,
        db: AsyncSession = Depends(get_session),
        password_in: ChangePasswordRequest,
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Change password for the authenticated user
    """
    user_service = UserService(db)
    result = await user_service.change_password(
        user_id=current_user.id,
        current_password=password_in.current_password,
        new_password=password_in.new_password
    )
    return {"success": result}
