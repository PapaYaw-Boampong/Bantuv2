from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from crud.user import UserCrud
from models.user import User
from services.token_service import TokenService, verify_password, get_password_hash
from sqlmodel import select
from datetime import datetime
from schemas.language import UserLanguageStatsUpdate


async def get_user_profile(
        user: User
) -> Dict[str, Any]:
    """
    Get a user's profile with statistics
    """

    return {
        "id": str(user.id),
        "username": user.username,
        "fullname": user.fullname,
        "email": user.email,
        "is_active": user.is_active,
        "role": user.role,
        "updated_at": user.updated_at,
        "created_at": user.created_at
    }


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserCrud(db)

    async def register_user(
            self,
            username: str,
            email: str,
            password: str,
            fullname: str,
            country: str
    ) -> User:
        """
        Register a new user with hashed password
        """
        if await self.repository.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

        if await self.repository.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        token_service = TokenService(self.db)
        hashed_password = get_password_hash(password)
        user_data = {
            "username": username,
            "email": email,
            "fullname": fullname,
            "hashed_password": hashed_password,
            "country": country
        }

        return await self.repository.create(user_data)

    async def authenticate_user(
            self,
            username_or_email: str,
            password: str
    ) -> Optional[User]:
        """
        Authenticate a user by username/email and password
        """
        user = await self.repository.get_by_username(username_or_email)
        if not user:
            user = await self.repository.get_by_email(username_or_email)

        if not user or not user.is_active or not verify_password(password, user.hashed_password):
            return None

        return user

    async def get_detailed_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by ID.
        """
        statement = select(User).where(User.id == user_id)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_all_profiles_detailed(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all users with pagination (ASYNC)
        """
        statement = select(User).offset(skip).limit(limit)
        results = await self.db.execute(statement)
        return list(results.scalars().all())

    async def update_user_profile(
            self,
            user_id: str,
            update_data: Dict[str, Any]
    ) -> User:
        """
        Update a user's profile
        """
        protected_fields = ['id', 'hashed_password', 'role', 'created_at']
        for field in protected_fields:
            update_data.pop(field, None)

        user = await self.repository.update_profile(user_id, update_data)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return user

    async def change_password(
            self,
            user: User,
            current_password: str,
            new_password: str
    ) -> bool:
        """
        Change a user's password
        """
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
        hashed_new_password = get_password_hash(new_password)
        await self.repository.update_profile(str(user.id), {"hashed_password": hashed_new_password})
        return True

    async def deactivate_user(
            self,
            user_id: str
    ) -> User:
        """
        Deactivate a user (soft delete)
        """
        user = await self.repository.update_profile(user_id, {"is_active": False})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return user

    async def delete(self, user_id: str) -> bool:
        """
        Delete a user (ASYNC)
        """
        user = await self.get_detailed_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.db.delete(user)
        await self.db.commit()
        return True

    async def update_user_stats(
            self,
            user_id: str,
            stats_data: UserLanguageStatsUpdate
    ) -> User:

        user = await self.get_detailed_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update general statistics
        user.total_hours_speech += stats_data.total_hours_speech
        user.total_sentences_translated += stats_data.total_sentences_translated
        user.total_annotation_tokens += stats_data.total_annotation_tokens

        # Update user's timestamp
        user.updated_at = datetime.utcnow()

        # Save changes
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get all statistics for a specific user

        Args:
            user_id: The ID of the user

        Returns:
            Dictionary containing user statistics
        """
        user = await self.get_detailed_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get the base stats from the user object
        stats = {
            "user_id": str(user.id),
            "username": user.username,
            "general_statistics": {
                "total_hours_speech": user.total_hours_speech,
                "total_sentences_translated": user.total_sentences_translated,
                "total_annotation_tokens": user.total_annotation_tokens,
            },
            "updated_at": user.updated_at.isoformat()
        }

        return stats
