from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import decode_token
from services.user_service import UserService
from models.user import User
from database import get_session  # Import your session dependency


# Dependency to get the current authenticated user
async def get_current_user(
        db: AsyncSession = Depends(get_session),
        token: str = Depends(decode_token)
) -> User:
    """Retrieve the currently authenticated user using UserService."""

    user_id = token.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)  # Instantiate the service
    user = await user_service.get_user_by_id(user_id)  # Use service method

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


# Dependency to get the current active user
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the user is active before granting access."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Dependency to check if the user is a superuser (admin)
async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the user is a superuser before granting admin access."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
