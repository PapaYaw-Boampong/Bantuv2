from typing import List, Optional, Dict, Any
from sqlmodel import select
from models.language import Language, UserLanguage
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime


class LanguageCrud:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, language_data: Dict[str, Any]) -> Language:
        """
        Create a new language (ASYNC)
        """
        language = Language(**language_data)
        self.db.add(language)
        await self.db.commit()
        await self.db.refresh(language)
        return language

    async def get_by_id(self, language_id: str) -> Optional[Language]:
        """
        Get a language by ID (ASYNC)
        """
        statement = select(Language).where(Language.id == language_id)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_code(self, language_code: str) -> Optional[Language]:
        """
        Get a language by ID (ASYNC)
        """
        statement = select(Language).where(Language.code == language_code)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> Optional[Language]:
        """
        Get a language by name (ASYNC)
        """
        statement = select(Language).where(Language.name == name)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Language]:
        """
        Get all languages with pagination (ASYNC)
        """
        statement = select(Language).offset(skip).limit(limit)
        results = await self.db.execute(statement)
        return list(results.scalars().all())

    async def update(self, language_id: str, update_data: Dict[str, Any]) -> Optional[Language]:
        """
        Update a language (ASYNC)
        """
        language = await self.get_by_id(language_id)
        if not language:
            return None

        for key, value in update_data.items():
            setattr(language, key, value)

        language.updated_at = datetime.utcnow()

        self.db.add(language)
        await self.db.commit()
        await self.db.refresh(language)
        return language

    async def delete(self, language_id: str) -> bool:
        """
        Delete a language (ASYNC)
        """
        language = await self.get_by_id(language_id)
        if not language:
            return False

        await self.db.delete(language)
        await self.db.commit()
        return True


class UserLanguageCrud:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_language_data: Dict[str, Any]) -> UserLanguage:
        """
        Create a user-language relationship (ASYNC)
        """
        user_language = UserLanguage(**user_language_data)
        self.db.add(user_language)
        await self.db.commit()
        await self.db.refresh(user_language)
        return user_language

    async def get_by_id(self, user_language_id: str) -> Optional[UserLanguage]:
        """
        Get a user-language relationship by ID (ASYNC)
        """
        return await self.db.get(UserLanguage, user_language_id)

    async def get_by_user_and_language(self, user_id: str, language_id: str) -> Optional[UserLanguage]:
        """
        Get user-language relationship by user ID and language ID (ASYNC)
        """
        statement = select(UserLanguage).where(
            UserLanguage.user_id == user_id,
            UserLanguage.language_id == language_id
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_languages_by_user(self, user_id: str, skip: int = 0, limit: int = 100) -> List[UserLanguage]:
        """
        Get all languages associated with a user (ASYNC)
        """
        statement = select(UserLanguage).where(UserLanguage.user_id == user_id).offset(skip).limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_users_by_language(self, language_id: str, skip: int = 0, limit: int = 100) -> List[UserLanguage]:
        """
        Get all users associated with a language (ASYNC)
        """
        statement = select(UserLanguage).where(UserLanguage.language_id == language_id).offset(skip).limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def update(self, user_language_id: str, update_data: Dict[str, Any]) -> Optional[UserLanguage]:
        """
        Update a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_id(user_language_id)
        if not user_language:
            return None

        for key, value in update_data.items():
            setattr(user_language, key, value)

        self.db.add(user_language)
        await self.db.commit()
        await self.db.refresh(user_language)
        return user_language

    async def delete(self, user_language_id: str) -> bool:
        """
        Delete a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_id(user_language_id)
        if not user_language:
            return False

        await self.db.delete(user_language)
        await self.db.commit()
        return True

    async def update_speech_hours(self, user_id: str, language_id: str, hours: int) -> UserLanguage:
        """
        Update speech hours for a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_user_and_language(user_id, language_id)

        if not user_language:
            user_language = await self.create({
                "user_id": user_id,
                "language_id": language_id,
                "total_hours_speech": hours,
                "total_sentences_translated": 0
            })
        else:
            user_language.total_hours_speech += hours
            self.db.add(user_language)
            await self.db.commit()
            await self.db.refresh(user_language)

        return user_language

    async def update_sentences_translated(self, user_id: str, language_id: str, sentences: int) -> UserLanguage:
        """
        Update sentences translated for a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_user_and_language(user_id, language_id)

        if not user_language:
            user_language = await self.create({
                "user_id": user_id,
                "language_id": language_id,
                "total_hours_speech": 0,
                "total_sentences_translated": sentences
            })
        else:
            user_language.total_sentences_translated += sentences
            self.db.add(user_language)
            await self.db.commit()
            await self.db.refresh(user_language)

        return user_language
