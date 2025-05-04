from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.v1.deps import get_current_active_user, get_current_superuser
from database import get_session
from services.user_service import UserService
from schemas.user import (
    UserUpdate,
    UserResponse,
    UserProfileResponse,
    TopContributorResponse
)
from models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_user(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user profile
    """
    user_service = UserService(db)
    profile = await user_service.get_detailed_user_by_id(str(current_user.id))
    return profile


@router.put("/me", response_model=UserResponse)
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
        user_id=str(current_user.id),
        update_data=user_in.model_dump(exclude_unset=True)
    )
    # Convert UUID fields to str before returning
    return {
        **user.model_dump(),
        "id": str(user.id),  # Ensure ID is a string
        "created_at": user.created_at.isoformat(),  # If needed
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }


@router.get("/top-contributors", response_model=List[TopContributorResponse])
async def get_top_contributors(
        time_period: Optional[int] = None,
        limit: int = 10,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get top contributors based on reputation score (Admin only)
    """
    user_service = UserService(db)
    top_users = await user_service.get_top_contributors(
        limit=limit,
        time_period=time_period
    )
    return top_users


# 🔹 Admin Endpoints
@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
        user_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get user by ID (Admin only)
    """
    user_service = UserService(db)
    profile = await user_service.get_detailed_user_by_id(user_id)
    return profile


@router.get("/users", response_model=UserProfileResponse)
async def get_user_by_id(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get user by ID (Admin only)
    """
    user_service = UserService(db)
    profile = await user_service.get_users
    return profile


@router.delete("/deactivate/{user_id}", response_model=Dict[str, bool])
async def deactivate_user(
        user_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Deactivate a user (Admin only)
    """
    user_service = UserService(db)
    await user_service.deactivate_user(user_id)
    return {"success": True}
