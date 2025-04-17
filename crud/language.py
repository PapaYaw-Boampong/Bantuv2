from typing import List, Optional, Dict, Any
from sqlmodel import select
from sqlalchemy.orm import joinedload
from models.language import Language
from models.user import UserLanguage
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID


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

    async def get_by_user_and_language(self, user_id: UUID, language_id: UUID, task_type: str) -> Optional[UserLanguage]:
        """
        Get a user-language relationship by user ID and language ID (ASYNC)
        """
        statement = (
            select(UserLanguage)
            .where(UserLanguage.user_id == user_id, UserLanguage.language_id == language_id)
            .where(UserLanguage.task_type == task_type)  # filter for task type
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

    async def update_speech_hours(self, user_id: UUID, language_id: UUID, hours: float, task_type: str) -> UserLanguage:
        """
        Update speech hours for a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_user_and_language(user_id, language_id, task_type)

        if not user_language:
            user_language = await self.create({
                "user_id": user_language.user_id,
                "language_id": user_language.language_id,
                "total_hours_speech": hours,
                "total_sentences_translated": 0,
                "total_annotation_tokens": 0
            })
        else:
            user_language.total_hours_speech += hours
            self.db.add(user_language)
            await self.db.commit()
            await self.db.refresh(user_language)

        return user_language

    async def update_sentences_translated(self, user_id: UUID, language_id: UUID, sentences: int,
                                          task_type: str) -> UserLanguage:
        """
        Update sentences translated for a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_user_and_language(user_id, language_id, task_type)

        if not user_language:
            user_language = await self.create({
                "user_id": user_language.user_id,
                "language_id": user_language.language_id,
                "total_hours_speech": 0,
                "total_sentences_translated": sentences,
                "total_annotation_tokens": 0
            })
        else:
            user_language.total_sentences_translated += sentences
            self.db.add(user_language)
            await self.db.commit()
            await self.db.refresh(user_language)

        return user_language

    async def update_annotation_tokens(self, user_id: UUID, language_id: UUID, tokens: int,
                                       task_type: str) -> UserLanguage:
        """
        Update annotation tokens for a user-language relationship (ASYNC)
        """
        user_language = await self.get_by_user_and_language(user_id, language_id, task_type)

        if not user_language:
            user_language = await self.create({
                "user_id": user_id,
                "language_id": language_id,
                "total_hours_speech": 0,
                "total_sentences_translated": 0,
                "total_annotation_tokens": tokens
            })
        else:
            user_language.total_annotation_tokens += tokens
            self.db.add(user_language)
            await self.db.commit()
            await self.db.refresh(user_language)

        return user_language

    async def update_stats(
            self,
            user_language: UserLanguage,
            hours: int = 0,
            sentences: int = 0,
            tokens: int = 0,
            is_contribution: bool = False,
            is_evaluation: bool = False,
            accepted: bool = False
    ) -> UserLanguage:
        user_language.total_hours_speech += hours
        user_language.total_sentences_translated += sentences
        user_language.total_annotation_tokens += tokens

        if is_contribution:
            user_language.contribution_count += 1
            if accepted:
                user_language.accepted_contributions += 1

        if is_evaluation:
            user_language.evaluation_count += 1
            if accepted:
                user_language.accepted_evaluations += 1

        # Update scores
        if user_language.contribution_count:
            user_language.contribution_acceptance_score = (
                    user_language.accepted_contributions / user_language.contribution_count
            )
        if user_language.evaluation_count:
            user_language.evaluation_acceptance_score = (
                    user_language.accepted_evaluations / user_language.evaluation_count
            )

        await self.db.commit()
        await self.db.refresh(user_language)
        return user_language

    async def update_language_stats(
            self,
            language_id: UUID,
            user_id: UUID,
            task_type: str,
            stats_data: dict
    ) -> Optional[UserLanguage]:

        user_language = await self.get_by_user_and_language(user_id, language_id, task_type)

        if not user_language:
            raise ValueError("UserLanguage not found")

        hours = stats_data.get("hours", 0)
        sentences = stats_data.get("sentences", 0)
        tokens = stats_data.get("tokens", 0)
        is_contribution = stats_data.get("is_contribution", False)
        is_evaluation = stats_data.get("is_evaluation", False)
        accepted = stats_data.get("accepted", False)

        return await self.update_stats(
            user_language,
            hours=hours,
            sentences=sentences,
            tokens=tokens,
            is_contribution=is_contribution,
            is_evaluation=is_evaluation,
            accepted=accepted,
        )
