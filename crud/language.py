from typing import List, Optional, Dict, Any
from sqlmodel import select
from sqlalchemy.orm import joinedload
from models.language import Language
from models.user import UserLanguage, UserLanguageStats
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException, status

PROFICIENCY_LEVELS = {
    "beginner": 3.0,
    "intermediate": 5.0,
    "advanced": 7.0,
    "native": 8.0,
}


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

    async def get_by_id(self, language_id: UUID) -> Optional[Language]:
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

    async def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            active: bool = False,
            inactive: bool = False,
            all_: bool = False
    ) -> List[Language]:
        """
        Get languages with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active: If True, return only active languages
            inactive: If True, return only inactive languages
            all: If True, return all languages regardless of status
        """
        statement = select(Language).offset(skip).limit(limit)

        # Apply filters based on parameters
        if not all_:
            if inactive:
                statement = statement.where(Language.is_active == False)
            elif active:
                statement = statement.where(Language.is_active == True)

        results = await self.db.execute(statement)
        return list(results.scalars().all())

    async def update(self, language_id: UUID, update_data: Dict[str, Any]) -> Optional[Language]:
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

    async def update_activation_status(self, language_id: UUID, is_active: bool, state: str) -> bool:
        """
        Update only the activation status of a language and return success status.
        """
        language = await self.get_by_id(language_id)
        if not language:
            raise HTTPException(status_code=404, detail="Language not found")

        if language.is_active and is_active or not language.is_active and not is_active:
            raise HTTPException(status_code=400, detail=f"Language is already in the requested state: {state} ")

        language.is_active = is_active
        language.updated_at = datetime.utcnow()

        self.db.add(language)
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

    async def get_by_id(self, user_language_id: UUID) -> Optional[UserLanguage]:
        """
        Get a user-language relationship by ID (ASYNC)
        """
        statement = (
            select(UserLanguage)
            .options(joinedload(UserLanguage.language))  # Join Language table
            .where(UserLanguage.id == user_language_id)
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_user_and_language(self, user_id: UUID, language_id: UUID) -> Optional[UserLanguage]:
        """
        Get a user-language relationship by user ID and language ID (ASYNC)
        """
        statement = (
            select(UserLanguage)
            .where(UserLanguage.user_id == user_id, UserLanguage.language_id == language_id)
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_languages_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[UserLanguage]:
        """
        Get all languages associated with a user (ASYNC)
        """
        statement = (
            select(UserLanguage)
            .options(joinedload(UserLanguage.language))  # Join Language table
            .where(UserLanguage.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_users_by_language(self, language_id: UUID, skip: int = 0, limit: int = 100) -> List[UserLanguage]:
        """
        Get all users associated with a language (ASYNC)
        """
        statement = select(UserLanguage).where(UserLanguage.language_id == language_id).offset(skip).limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def delete(self, user_language_id: UUID) -> bool:
        """
        Delete a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_id(user_language_id)
        if not user_language:
            return False

        await self.db.delete(user_language)
        await self.db.commit()
        return True

    async def update_stats(
            self,
            user_language: UserLanguage,
            hours: int = 0,
            sentences: int = 0,
            tokens: int = 0,
    ) -> UserLanguage:
        user_language.total_hours_speech += hours
        user_language.total_sentences_translated += sentences
        user_language.total_annotation_tokens += tokens

        await self.db.commit()
        await self.db.refresh(user_language)
        return user_language

    async def update_language_stats(
            self,
            language_id: UUID,
            user_id: UUID,
            stats_data: dict
    ) -> Optional[UserLanguage]:

        user_language = await self.get_by_user_and_language(user_id, language_id)

        if not user_language:
            raise ValueError("UserLanguage not found")

        hours = stats_data.get("hours", 0)
        sentences = stats_data.get("sentences", 0)
        tokens = stats_data.get("tokens", 0)

        return await self.update_stats(
            user_language,
            hours=hours,
            sentences=sentences,
            tokens=tokens
        )


class UserLanguageStatsCrud:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_language_stats_data: Dict[str, Any]) -> UserLanguageStats:
        """
        Create a user-language relationship (ASYNC)
        """
        user_language_stats = UserLanguageStats(**user_language_stats_data)
        self.db.add(user_language_stats)
        await self.db.commit()
        await self.db.refresh(user_language_stats)
        return user_language_stats

    async def get_by_id(self, user_language_stats_id: UUID) -> Optional[UserLanguageStats]:
        """
        Get a user-language relationship by ID (ASYNC)
        """
        statement = (
            select(UserLanguageStats)
            .where(UserLanguageStats.id == user_language_stats_id)
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_user_and_language_task_type(self, user_id: UUID, language_id: UUID, task_type: str
                                                 ) -> Optional[UserLanguageStats]:
        """
        Get a user-language relationship by user ID, language ID, and task type (ASYNC)
        """
        statement = (
            select(UserLanguageStats)
            .where(UserLanguageStats.user_language_id == user_id,
                   UserLanguageStats.language_id == language_id,
                   UserLanguageStats.task_type == task_type)
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def update_proficiency(
            self,
            user_language_stats_id: UUID,
            proficiency: float
    ) -> UserLanguageStats:
        user_language_stats = await self.get_by_id(user_language_stats_id)
        if not user_language_stats:
            raise ValueError("user stats not found")
        user_language_stats.proficiency = proficiency
        user_language_stats.updated_at = datetime.utcnow()

        self.db.add(user_language_stats)
        await self.db.commit()
        await self.db.refresh(user_language_stats)
        return user_language_stats

    async def update_stats(
            self,
            user_language_stats: UserLanguageStats,
            is_contribution: bool = False,
            is_evaluation: bool = False,
            accepted: bool = False
    ) -> UserLanguageStats:
        if is_contribution:
            user_language_stats.contribution_count += 1
            if accepted:
                user_language_stats.accepted_contributions += 1
            # Update scores
            if user_language_stats.contribution_count:
                user_language_stats.contribution_acceptance_score = (
                        user_language_stats.accepted_contributions / user_language_stats.contribution_count
                )

        if is_evaluation:
            user_language_stats.evaluation_count += 1
            if accepted:
                user_language_stats.accepted_evaluations += 1

            if user_language_stats.evaluation_count:
                user_language_stats.evaluation_acceptance_score = (
                        user_language_stats.accepted_evaluations / user_language_stats.evaluation_count
                )

        await self.db.commit()
        await self.db.refresh(user_language_stats)
        return user_language_stats

    async def update_language_stats(
            self,
            language_id: UUID,
            user_id: UUID,
            task_type: str,
            stats_data: dict
    ) -> Optional[UserLanguageStats]:

        user_language_stats = await self.get_by_user_and_language_task_type(user_id, language_id, task_type)
        if not user_language_stats:
            user_language = await UserLanguageCrud(self.db).get_by_user_and_language(user_id, language_id)
            if not user_language:
                raise ValueError("UserLanguage not found")

            await self.create({
                "user_language_id": user_language.id,
                "task_type": task_type,
                "proficiency": PROFICIENCY_LEVELS.get(user_language.proficiency, 3.0),
            })

        is_contribution = stats_data.get("is_contribution", False)
        is_evaluation = stats_data.get("is_evaluation", False)
        accepted = stats_data.get("accepted", False)

        return await self.update_stats(
            user_language_stats,
            is_contribution=is_contribution,
            is_evaluation=is_evaluation,
            accepted=accepted,
        )



