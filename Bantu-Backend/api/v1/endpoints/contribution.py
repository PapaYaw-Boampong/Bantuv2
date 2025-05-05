from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from database import get_session
from models.user import User
from schemas.contribution import (
    ContributionCreate,
    CustomContributionCreate
)
from services.contribution_service import ContributionManagementService
from api.v1.deps import get_current_active_user, get_current_superuser

router = APIRouter()


# ======== CREATE ========

@router.post("/{contribution_type}/", summary="Create a new contribution")
async def create_contribution(
        language_id: UUID,
        sample_id: UUID,
        contribution_type: str,
        data: ContributionCreate,
        db: AsyncSession = Depends(get_session),
        user: User = Depends(get_current_active_user)
):
    service = ContributionManagementService(db)
    try:
        return await service.create_contribution(
            user_id=user.user_id,
            contribution_type=contribution_type,
            sample_id=sample_id,
            data=data,
            language_id=language_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contribution_type}/custom/", summary="Create a custom contribution")
async def create_custom_contribution(
        language_id: UUID,
        contribution_type: str,
        contribution_data: CustomContributionCreate,
        db: AsyncSession = Depends(get_session),
        user: User = Depends(get_current_active_user)
):
    service = ContributionManagementService(db)
    try:
        return await service.create_custom_contribution(
            user_id=user.user_id,
            language_id=language_id,
            contribution_data=contribution_data,
            contribution_type=contribution_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
