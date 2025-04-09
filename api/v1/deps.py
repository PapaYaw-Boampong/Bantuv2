from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session  # Import database session dependency

from services.user_service import UserService
from services.token_service import TokenService  # Import new TokenService
from models.user import User

# Define OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Dependency to get the current authenticated user
async def get_current_user(
    db: AsyncSession = Depends(get_session),
    token: str = Security(oauth2_scheme)
) -> User:
    """
    Retrieve the currently authenticated user using TokenService.

    Args:
        db: Database session dependency.
        token: JWT access token from Authorization header.

    Returns:
        The authenticated user object.
    """
    token_service = TokenService(db)  # Initialize token service

    try:
        payload = token_service.decode_token(token)  # Verify & decode token
        user_id = payload.get("sub")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user_service = UserService(db)
    user = await user_service.get_detailed_user_by_id(user_id)

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

    if not (current_user.role != 3 or current_user.role != 2):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Current role status: " + str(current_user.role)
        )
    return current_user
