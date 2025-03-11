from typing import List, Optional, Dict, Any
from sqlmodel import select
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


class UserCrud:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_data: Dict[str, Any]) -> User:
        """
        Create a new user (ASYNC)
        """
        user = User(**user_data)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID (ASYNC)
        """
        statement = select(User).where(User.id == user_id)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username (ASYNC)
        """
        statement = select(User).where(User.username == username)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email (ASYNC)
        """
        statement = select(User).where(User.email == email)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all users with pagination (ASYNC)
        """
        statement = select(User).offset(skip).limit(limit)
        results = await self.db.execute(statement)
        return list(results.scalars().all())

    async def update(self, user_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        """
        Update a user (ASYNC)
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.utcnow()

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def increment_contribution_stats(
            self,
            user_id: str,
            is_accepted: bool = False,
            hours_speech: int = 0,
            sentences_translated: int = 0,
            tokens_produced: int = 0,
            points: int = 0
    ) -> Optional[User]:
        """
        Increment a user's contribution statistics (ASYNC)
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.contribution_count += 1
        if is_accepted:
            user.accepted_contributions += 1

        user.total_hours_speech += hours_speech
        user.total_sentences_translated += sentences_translated
        user.total_tokens_produced += tokens_produced
        user.total_points += points
        user.updated_at = datetime.utcnow()

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: str) -> bool:
        """
        Delete a user (ASYNC)
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await self.db.delete(user)
        await self.db.commit()
        return True

    async def search_users(
            self,
            username: Optional[str] = None,
            email: Optional[str] = None,
            is_active: Optional[bool] = None,
            min_reputation: Optional[float] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[User]:
        """
        Search for users with various filters (ASYNC)
        """
        query = select(User)

        if username:
            query = query.where(User.username.contains(username))

        if email:
            query = query.where(User.email.contains(email))

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        if min_reputation is not None:
            query = query.where(User.reputation_score >= min_reputation)

        query = query.offset(skip).limit(limit)

        results = await self.db.execute(query)
        return list(results.scalars().all())

    async def calculate_reputation_score(self, user_id: str) -> Optional[float]:
        """
        Calculate and update a user's reputation score (ASYNC)
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if user.contribution_count > 0:
            acceptance_rate = user.accepted_contributions / user.contribution_count
            volume_factor = 1 + (user.contribution_count / 10)

            user.reputation_score = min(100, int(acceptance_rate * volume_factor * 20))
        else:
            user.reputation_score = 0

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user.reputation_score



