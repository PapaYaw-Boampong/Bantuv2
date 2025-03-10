from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from crud.language import LanguageCrud, UserLanguageCrud
from models.language import Language, UserLanguage


class LanguageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.language_repository = LanguageCrud(db)
        self.user_language_repository = UserLanguageCrud(db)

    # --- Language Related Operations ---
    async def create_language(self, language_data: Dict[str, Any]) -> Language:
        """
        Create a new language if it doesn't already exist.
        """
        if await self.language_repository.get_by_code(language_data.get("code")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="A language with this code already exists.")

        return await self.language_repository.create(language_data)

    async def get_language(self, term: str) -> Optional[Language]:
        """
        Retrieve a language by ID, code, or name.
        """
        if term.isdigit():  # assume ID is numeric
            language = await self.language_repository.get_by_id(term)
        elif len(term) == 3:  # assume code is 3-letter ISO code
            language = await self.language_repository.get_by_code(term)
        else:  # assume name
            language = await self.language_repository.get_by_name(term)

        if not language:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Language not found.")
        return language

    async def get_all_languages(self, skip: int = 0, limit: int = 100) -> List[Language]:
        """
        Retrieve all available languages with pagination.
        """
        return await self.language_repository.get_all(skip, limit)

    async def update_language(self, language_id: str, update_data: Dict[str, Any]) -> Language:
        """
        Update a language if it exists.
        """
        language = await self.language_repository.update(language_id, update_data)
        if not language:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Language not found.")
        return language

    async def delete_language(self, language_id: str) -> bool:
        """
        Delete a language if it exists.
        """
        deleted = await self.language_repository.delete(language_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Language not found.")
        return deleted

    # --- User-Language Related Operations ---

    async def add_user_language(self, user_id: str, language_id: str) -> UserLanguage:
        """
        Associate a user with a language.
        """
        try:
            return await self.user_language_repository.create({"user_id": user_id, "language_id": language_id})
        except IntegrityError as e:
            # Handle the error, e.g., raise a custom exception or return an error response
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="A language with this code already exists.")

    async def get_user_languages(self, user_id: str, skip: int = 0, limit: int = 100) -> List[UserLanguage]:
        """
        Get all languages associated with a user.
        """
        return await self.user_language_repository.get_languages_by_user(user_id, skip, limit)

    async def remove_user_language(self, user_language_id: str) -> bool:
        """
        Remove a language from a user.
        """
        deleted = await self.user_language_repository.delete(user_language_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User-Language association not found.")
        return deleted

    async def update_speech_hours(self, user_id: str, language_id: str, hours: int) -> UserLanguage:
        """
        Update the total speech hours for a user in a specific language.
        """
        return await self.user_language_repository.update_speech_hours(user_id, language_id, hours)

    async def update_sentences_translated(self, user_id: str, language_id: str, sentences: int) -> UserLanguage:
        """
        Update the total number of sentences translated for a user in a specific language.
        """
        return await self.user_language_repository.update_sentences_translated(user_id, language_id, sentences)
