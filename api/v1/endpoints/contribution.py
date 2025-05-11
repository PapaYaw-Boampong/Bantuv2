from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from database import get_session
from models.user import User
from schemas.contribution import (
    ContributionCreate,
    ContributionStats
)
from services.contribution_service import ContributionManagementService
from services.challenge_service import ChallengeService
from api.v1.deps import get_current_active_user, get_current_superuser
from core.config import settings

router = APIRouter()


# Dependencies
def get_contribution_service(db: AsyncSession = Depends(get_session)):
    return ContributionManagementService(db)


def get_challenge_service(db: AsyncSession = Depends(get_session)):
    return ChallengeService(db)


# ======== CREATE ========

@router.post("/{contribution_type}/", summary="Create a new contribution")
async def create_contribution(
        language_id: UUID,
        sample_id: UUID,
        contribution_type: str,
        data: ContributionCreate,
        challenge_id: Optional[UUID] = None,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    service = get_contribution_service(db)
    try:
        return await service.create_contribution(
            user_id=current_user.id,
            contribution_type=contribution_type,
            sample_id=sample_id,
            data=data,
            language_id=language_id,
            challenge_id=challenge_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contribution_type}/custom/", summary="Create a custom contribution")
async def create_custom_contribution(
        language_id: UUID,
        contribution_type: str,
        contribution_data: ContributionCreate,
        challenge_id: Optional[UUID] = None,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    service = get_contribution_service(db)
    try:
        return await service.create_custom_contribution(
            user_id=current_user.id,
            language_id=language_id,
            contribution_data=contribution_data,
            contribution_type=contribution_type,
            challenge_id=challenge_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======== READ ========

@router.get("/stats/", summary="Get contribution statistics")
async def get_contribution_stats(
        contribution_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
        service: ContributionManagementService = Depends(get_contribution_service),
        current_user: User = Depends(get_current_active_user)
):
    # If no user_id provided, get stats for the current user
    if not user_id:
        user_id = current_user.id

    try:
        return await service.get_user_contribution_stats(user_id, contribution_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{contribution_type}/{contribution_id}/flag", summary="Flag contribution for review")
async def flag_contribution(
        contribution_id: UUID,
        contribution_type: str,
        service: ContributionManagementService = Depends(get_contribution_service),
        current_user: User = Depends(get_current_active_user)
):
    try:
        await service.flag_contribution(contribution_id, contribution_type)
        return {"message": f"{contribution_type.capitalize()} contribution flagged for review"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
