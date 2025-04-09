from typing import List, Optional, Dict, Any
from sqlmodel import select
from models.user import User, UserLanguage
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

    async def update_profile(self, user, update_data: Dict[str, Any]) -> Optional[User]:
        """
        Update a user (ASYNC)
        """
        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.utcnow()

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

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
            query = query.where(User.username.like(f"%{username}%"))

        if email:
            query = query.where(User.email.like(f"%{username}%"))

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        if min_reputation is not None:
            query = query.where(User.reputation_score >= min_reputation)

        query = query.offset(skip).limit(limit)

        results = await self.db.execute(query)
        return list(results.scalars().all())

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
