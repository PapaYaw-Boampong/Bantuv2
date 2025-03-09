from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from api.v1.deps import get_current_user, get_current_active_user, get_current_superuser
from database import get_session
from services.user_service import UserService
from core.security import create_access_token
from core.config import settings
from schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfileResponse,
    Token,
    ChangePasswordRequest,
    TopContributorResponse
)
from models.user import User

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
    return user


@router.post("/login", response_model=Token)
async def login(
        db: AsyncSession = Depends(get_session),
        form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Get access token for user authentication
    """
    user_service = UserService(db)
    user = await user_service.authenticate_user(
        username_or_email=form_data.username,  # OAuth2 form uses username field
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/user", response_model=UserProfileResponse)
async def get_user(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user profile
    """
    user_service = UserService(db)
    profile = await user_service.get_user_profile(current_user.id)
    return profile


@router.put("/user", response_model=UserResponse)
async def update_user(
        *,
        db: AsyncSession = Depends(get_session),
        user_in: UserUpdate,
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update current user profile
    """
    user_service = UserService(db)
    user = await user_service.update_user_profile(
        user_id=current_user.id,
        update_data=user_in.dict(exclude_unset=True)
    )
    return user


@router.post("/user/change-password", response_model=Dict[str, bool])
async def change_password(
        *,
        db: AsyncSession = Depends(get_session),
        password_in: ChangePasswordRequest,
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Change current user password
    """
    user_service = UserService(db)
    result = await user_service.change_password(
        user_id=current_user.id,
        current_password=password_in.current_password,
        new_password=password_in.new_password
    )
    return {"success": result}


@router.get("/top-contributors", response_model=List[TopContributorResponse])
async def get_top_contributors(
        time_period: Optional[int] = None,
        limit: int = 10,
        db: AsyncSession = Depends(get_session)
) -> Any:
    """
    Get top contributors based on reputation score
    """
    user_service = UserService(db)
    top_users = await user_service.get_top_contributors(
        limit=limit,
        time_period=time_period
    )
    return top_users


# Admin endpoints
@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
        user_id: str,
        db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Get user by ID (admin only)
    """
    user_service = UserService(db)
    profile = await user_service.get_user_profile(user_id)
    return profile


@router.delete("/{user_id}", response_model=Dict[str, bool])
async def deactivate_user(
        user_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Deactivate a user (admin only)
    """
    user_service = UserService(db)
    await user_service.deactivate_user(user_id)
    return {"success": True}
