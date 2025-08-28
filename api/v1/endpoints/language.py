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
from api.v1.deps import get_current_active_user, get_current_superuser
from pydantic import UUID4

router = APIRouter()


# -------------------- Language Routes --------------------
@router.post(
    "/new",
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


@router.put(
    "/{language_id}",
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
    return await language_service.update_language(UUID4(language_id), language_in.model_dump())


@router.put(
    "/activate/{language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="activate a language"
)
async def activate_language(
        db: AsyncSession = Depends(get_session),
        language_id: str = Path(...),
        current_user: User = Depends(get_current_superuser)
) -> None:
    """Delete a language (admin only)."""
    language_service = LanguageService(db)
    await language_service.activate_language(language_id)


@router.put(
    "/deactivate/{language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="deactivate a language"
)
async def deactivate_language(
        db: AsyncSession = Depends(get_session),
        language_id: str = Path(...),
        current_user: User = Depends(get_current_superuser)
) -> None:
    """Delete a language (admin only)."""
    language_service = LanguageService(db)
    await language_service.deactivate_language(language_id)


@router.get(
    "/languages",
    response_model=List[LanguageRead],
    summary="Get all languages"
)
async def read_languages(
        db: AsyncSession = Depends(get_session),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        current_user: User = Depends(get_current_active_user)
) -> Any:

    language_service = LanguageService(db)
    """Retrieve all languages with pagination."""
    return await language_service.get_all_languages(skip, limit)


@router.get(
    "/{language_id}",
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


# -------------------- UserLanguage Routes --------------------

@router.post(
    "/userlanguages/add",
    response_model=UserLanguageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a language to a user"
)
async def assign_language_to_user(
        user_language_in: UserLanguageCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """Assign a language to a user."""
    language_service = LanguageService(db)
    return await language_service.add_user_language(
        current_user.id,
        user_language_in.language_id,
        user_language_in.proficiency)


@router.get(
    "/userlanguages/me",
    response_model=List[UserLanguageRead],
    summary="Get languages assigned to a user"
)
async def get_languages_by_user(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve languages assigned to a specific user."""
    language_service = LanguageService(db)
    return await language_service.get_user_languages(current_user.id)


@router.delete(
    "/userlanguages/{user_language_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user-language relationship"
)
async def delete_user_language(
        db: AsyncSession = Depends(get_session),
        user_language_id: str = Path(...),
        current_user: User = Depends(get_current_active_user)
) -> None:
    """Delete user-language relationship."""
    language_service = LanguageService(db)
    await language_service.remove_user_language(user_language_id)


@router.get(
    "/userlanguages/{user_language_id}/stats",
    response_model=List[dict],
    summary="Get statistics for a user-language relationship"
)
async def get_user_language_stats(
        db: AsyncSession = Depends(get_session),
        user_language_id: str = Path(...),
        current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get detailed statistics for a user-language relationship."""
    language_service = LanguageService(db)
    return await language_service.user_language_stats_repository.get_user_language_stats(user_language_id)


