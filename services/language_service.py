import uuid
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from crud.language import LanguageCrud, UserLanguageCrud, UserLanguageStatsCrud
from datetime import datetime
from models.language import Language
from models.user import UserLanguage


class LanguageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.language_repository = LanguageCrud(db)
        self.user_language_repository = UserLanguageCrud(db)
        self.user_language_stats_repository = UserLanguageStatsCrud(db)

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
        Retrieve a language by UUID, ISO code, or name.
        Priority: UUID > Code (3-letter) > Name
        """
        language = None

        # Try to parse as UUID
        try:
            language_id = uuid.UUID(term.strip())
            language = await self.language_repository.get_by_id(language_id)
        except ValueError:
            pass  # Not a UUID, proceed to check code or name

        # If not found by UUID and it's a 3-letter code
        if not language and len(term) == 3 and term.isalpha():
            language = await self.language_repository.get_by_code(term.lower())

        # If still not found, try by name
        if not language:
            language = await self.language_repository.get_by_name(term.strip())

        if not language:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Language not found.")

        return language

    async def get_all_languages(
            self,
            skip: int = 0,
            limit: int = 100,
            active: bool = True,
            inactive: bool = False,
            all_: bool = False
    ) -> List[Language]:
        """
        Retrieve all available languages with pagination.
        """

        if all_:
            active, inactive = False, False
        elif inactive:
            active = False

        languages = await self.language_repository.get_all(
            skip,
            limit,
            active=active,
            inactive=inactive,
            all_=all_)

        if not languages:
            return []  # Explicitly return an empty list (optional)

        for language in languages:
            language.id = str(language.id)

        return languages

    async def update_language(self, language_id: str, update_data: Dict[str, Any]) -> Language:
        """
        Update a language if it exists.
        """
        language = await self.language_repository.update(language_id, update_data)
        if not language:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Language not found.")
        language.id = str(language.id)
        return language

    async def activate_language(self, language_id: str) -> bool:

        try:
            language_id = uuid.UUID(language_id.strip())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid language ID format.")

        return await self.language_repository.update_activation_status(
            language_id,
            True,
            state="active"
        )

    async def deactivate_language(self, language_id: str) -> bool:

        try:
            language_id = uuid.UUID(language_id.strip())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid language ID format.")

        return await self.language_repository.update_activation_status(
            language_id,
            False,
            state="inactive"
        )

    # --- User-Language Related Operations ---
    async def add_user_language(self, user_id: str, language_id: str, proficiency: str) -> dict:
        """
        Associate a user with a language.
        """

        try:
            language_id = uuid.UUID(language_id.strip())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid language ID format.")

        try:
            pair = await self.user_language_repository.create(
                {"user_id": user_id, "language_id": language_id, "proficiency": proficiency})
            if pair:
                entry = await self.user_language_repository.get_by_id(pair.id)

                language_data = {
                    "association_id": str(entry.id),  # The UserLanguage ID
                    "proficiency": str(entry.proficiency),  # The associated language ID
                    "language": {
                        "id": str(entry.language.id),
                        "name": entry.language.name,
                        "code": entry.language.code if hasattr(entry.language, "code") else None,
                    }
                }
                return language_data

        except IntegrityError as e:
            # Handle the error, e.g., raise a custom exception or return an error response
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="A language with this code already exists.")

    async def get_user_languages(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[dict]:
        """
        Get all languages associated with a user.
        """
        pairs = await self.user_language_repository.get_languages_by_user(user_id, skip, limit)
        languages_data = []
        for entry in pairs:
            languages_data.append({
                "association_id": str(entry.id),  # The UserLanguage ID
                "proficiency": entry.proficiency,
                "language": {
                    "id": str(entry.language.id),
                    "name": entry.language.name,
                    "code": entry.language.code if hasattr(entry.language, "code") else None,
                    "description": entry.language.description
                }
            })

        return languages_data

    async def remove_user_language(self, user_language_id: str) -> bool:
        """
        Remove a language from a user.
        """
        try:
            pair_id = uuid.UUID(user_language_id.strip())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid language ID format.")
        deleted = await self.user_language_repository.delete(pair_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User-Language association not found.")
        return deleted
