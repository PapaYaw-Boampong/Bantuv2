from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from crud.user import UserCrud
from models.user import User
from core.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserCrud(db)

    async def register_user(
            self,
            username: str,
            email: str,
            password: str
    ) -> User:
        """
        Register a new user with hashed password
        """
        if await self.repository.get_by_username(username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

        if await self.repository.get_by_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        hashed_password = get_password_hash(password)
        user_data = {"username": username, "email": email, "hashed_password": hashed_password}

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

    async def get_user_profile(
            self,
            user_id: str
    ) -> Dict[str, Any]:
        """
        Get a user's profile with statistics
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.repository.calculate_reputation_score(user_id)

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "contribution_count": user.contribution_count,
            "accepted_contributions": user.accepted_contributions,
            "reputation_score": user.reputation_score,
            "total_hours_speech": user.total_hours_speech,
            "total_sentences_translated": user.total_sentences_translated,
            "total_tokens_produced": user.total_tokens_produced,
            "total_points": user.total_points,
            "acceptance_rate": (user.accepted_contributions / user.contribution_count if user.contribution_count > 0 else 0) * 100,
        }

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by ID.
        """
        return await self.repository.get_by_id(user_id)

    async def update_user_profile(
            self,
            user_id: str,
            update_data: Dict[str, Any]
    ) -> User:
        """
        Update a user's profile
        """
        protected_fields = ['id', 'hashed_password', 'is_superuser', 'created_at', 'reputation_score']
        for field in protected_fields:
            update_data.pop(field, None)

        user = await self.repository.update(user_id, update_data)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return user

    async def change_password(
            self,
            user_id: str,
            current_password: str,
            new_password: str
    ) -> bool:
        """
        Change a user's password
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

        hashed_new_password = get_password_hash(new_password)
        await self.repository.update(user_id, {"hashed_password": hashed_new_password})
        return True

    async def deactivate_user(
            self,
            user_id: str
    ) -> User:
        """
        Deactivate a user (soft delete)
        """
        user = await self.repository.update(user_id, {"is_active": False})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return user

    async def get_top_contributors(
            self,
            limit: int = 10,
            time_period: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top contributors based on reputation score
        """
        users = await self.repository.get_all(limit=100)
        users.sort(key=lambda user: user.reputation_score, reverse=True)
        top_users = users[:limit]

        return [{
            "id": user.id,
            "username": user.username,
            "reputation_score": user.reputation_score,
            "contribution_count": user.contribution_count,
            "accepted_contributions": user.accepted_contributions,
            "total_points": user.total_points,
        } for user in top_users]

    async def record_contribution_activity(
            self,
            user_id: str,
            is_accepted: bool = False,
            hours_speech: int = 0,
            sentences_translated: int = 0,
            tokens_produced: int = 0,
            points: int = 0
    ) -> User:
        """
        Record a user's contribution activity and update their statistics
        """
        user = await self.repository.increment_contribution_stats(
            user_id=user_id,
            is_accepted=is_accepted,
            hours_speech=hours_speech,
            sentences_translated=sentences_translated,
            tokens_produced=tokens_produced,
            points=points
        )

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.repository.calculate_reputation_score(user_id)
        return user
