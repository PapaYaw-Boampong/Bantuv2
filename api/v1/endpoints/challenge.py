from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from database import get_session
from models.challenge import Challenge
from models.user import User
from services.challenge_service import ChallengeService
from schemas.challenge import (
    ChallengeCreate,
    ChallengeUpdate,
    ChallengeSummary,
    ChallengeParticipantResponse,
    UserStatsUpdate
)
from api.v1.deps import get_current_active_user, get_current_superuser

router = APIRouter(prefix="/challenges", tags=["challenges"])


# Dependency

def get_challenge_service(db: AsyncSession = Depends(get_session)):
    return ChallengeService(db)


@router.post("/create", response_model=Challenge)
async def create_challenge(
        challenge_data: ChallengeCreate,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a new challenge."""
    return await challenge_service.create_challenge(challenge_data.model_dump())


@router.get("/{challenge_id}", response_model=Challenge)
async def get_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to get"),
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get a specific challenge by ID."""
    challenge = await challenge_service.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.get("/", response_model=List[Challenge])
async def get_challenges(
        active_only: bool = Query(False, description="Only return active challenges"),
        skip: int = Query(0, description="Skip the first N challenges"),
        limit: int = Query(100, description="Limit the number of challenges returned"),
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get all challenges with pagination."""
    if active_only:
        return await challenge_service.get_active_challenges(skip=skip, limit=limit)
    return await challenge_service.get_all_challenges(skip=skip, limit=limit)


@router.put("/{challenge_id}", response_model=Challenge)
async def update_challenge(
        challenge_data: ChallengeUpdate,
        challenge_id: str = Path(..., description="The ID of the challenge to update"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Update a challenge's information."""
    challenge = await challenge_service.update_challenge(challenge_id, challenge_data.model_dump(exclude_unset=True))
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.get("/summary", response_model=List[ChallengeSummary])
async def get_challenge_summaries(
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get summarized information about all challenges."""
    return await challenge_service.get_challenge_summary()


@router.get("/{challenge_id}/leaderboard", response_model=List[ChallengeParticipantResponse])
async def get_challenge_leaderboard(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        limit: int = Query(10, description="Number of top participants to return"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get the leaderboard for a specific challenge."""
    leaderboard = await challenge_service.get_leaderboard(challenge_id, limit=limit)
    return leaderboard


@router.post("/{challenge_id}/register/{user_id}", response_model=Dict[str, Any])
async def register_user_to_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        user_id: str = Path(..., description="The ID of the user to register"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Register a user to a challenge."""
    try:
        return await challenge_service.register_user_to_challenge(challenge_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{challenge_id}/participants/{user_id}/stats", response_model=Dict[str, Any])
async def update_user_stats(
        stats_update: UserStatsUpdate,
        challenge_id: str = Path(..., description="The ID of the challenge"),
        user_id: str = Path(..., description="The ID of the user"),
        update_points: bool = Query(False, description="Whether to update the user's points"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Update a user's statistics for a specific challenge."""
    try:
        return await challenge_service.update_user_stats(
            challenge_id,
            user_id,
            stats_update.model_dump(exclude_unset=True),
            update_points=update_points
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{challenge_id}/end", response_model=Challenge)
async def end_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to end"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """End a challenge and finalize statistics."""
    challenge = await challenge_service.end_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.get("/{challenge_id}/participants/{user_id}", response_model=Dict[str, Any])
async def get_user_challenge_stats(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        user_id: str = Path(..., description="The ID of the user"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Get a specific user's statistics for a challenge."""
    crud = challenge_service.crud
    stats = await crud.get_user_challenge_stats(challenge_id, user_id)
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not registered for challenge {challenge_id}"
        )
    return stats
