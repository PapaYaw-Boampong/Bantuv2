from typing import Any, List
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from models.user import User
from database import get_session
from schemas.language import (
    LanguageCreate,
    LanguageUpdate,
    LanguageRead,
    UserLanguageCreate,
    UserLanguageRead,
)
from services.language_service import LanguageService
from api.v1.deps import get_current_user, get_current_superuser

router = APIRouter()

# -------------------- Language Routes --------------------

@router.post(
    "/languages/",
    response_model=LanguageCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new language"
)
async def create_language(
        language_in: LanguageCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
) -> Any:
    language_service = LanguageService(db)
    """Create a new language"""
    language_data = language_in.model_dump()
    return await language_service.create_language(language_data)


@router.get(
    "/languages/",
    response_model=List[LanguageRead],
    summary="Get all languages"
)
async def read_languages(
        db: AsyncSession = Depends(get_session),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100)
) -> Any:
    language_service = LanguageService(db)
    """Retrieve all languages with pagination."""
    return await language_service.get_all_languages(skip, limit)


@router.get(
    "/languages/{language_id}",
    response_model=LanguageRead,
    summary="Get a language by ID"
)
async def read_language(
        db: AsyncSession = Depends(get_session),
        language_id: str = Path(...)
) -> Any:
    language_service = LanguageService(db)
    """Get a language by ID."""
    return await language_service.get_language(term=language_id)


@router.put(
    "/languages/{language_id}",
    response_model=LanguageUpdate,
    summary="Update a language"
)
async def update_language(
        language_in: LanguageUpdate,
        db: AsyncSession = Depends(get_session),
        language_id: str = Path(...),

        current_user: User = Depends(get_current_superuser)
) -> Any:
    """Update a language (admin only)."""
    language_service = LanguageService(db)
    return await language_service.update_language(language_id, language_in.model_dump())


@router.delete(
    "/languages/{language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a language"
)
async def delete_language(
        db: AsyncSession = Depends(get_session),
        language_id: str = Path(...),
        current_user: User = Depends(get_current_superuser)
) -> None:
    """Delete a language (admin only)."""
    language_service = LanguageService(db)
    await language_service.delete_language(language_id)


# -------------------- UserLanguage Routes --------------------

@router.post(
    "/user-languages/",
    response_model=UserLanguageCreate,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a language to a user"
)
async def assign_language_to_user(
        user_language_in: UserLanguageCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user)
) -> Any:
    """Assign a language to a user."""
    language_service = LanguageService(db)
    return await language_service.add_user_language(
        user_language_in.user_id,
        user_language_in.language_id)


@router.get(
    "/user-languages/{user_id}",
    response_model=List[UserLanguageRead],
    summary="Get languages assigned to a user"
)
async def get_languages_by_user(
        db: AsyncSession = Depends(get_session),
        user_id: str = Path(...)
) -> Any:
    """Retrieve languages assigned to a specific user."""
    language_service = LanguageService(db)
    return await language_service.get_user_languages(user_id)


@router.delete(
    "/user-languages/{user_language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user-language relationship"
)
async def delete_user_language(
        db: AsyncSession = Depends(get_session),
        user_language_id: str = Path(...),
        current_user: User = Depends(get_current_user)
) -> None:
    """Delete user-language relationship."""
    language_service = LanguageService(db)
    await language_service.remove_user_language(user_language_id)
