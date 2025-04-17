from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from database import get_session
from models.challenge import Challenge, ChallengeStatus
from models.user import User
from schemas.challenge import (
    ChallengeCreate,
    ChallengeUpdate,
    ChallengeParticipationCreate,
    ChallengeParticipationUpdate,
    GetChallenges,
)
from services.challenge_service import ChallengeService
from api.v1.deps import get_current_active_user, get_current_superuser

router = APIRouter()


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
    return await challenge_service.create_challenge(challenge_data)


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
        query_params: GetChallenges = Depends(),
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get all challenges with filters and pagination."""
    return await challenge_service.list_challenges(query_params)


@router.put("/{challenge_id}", response_model=Challenge)
async def update_challenge(
        challenge_data: ChallengeUpdate,
        challenge_id: str = Path(..., description="The ID of the challenge to update"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Update a challenge's information."""
    challenge = await challenge_service.update_challenge(challenge_id, challenge_data)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.delete("/{challenge_id}", response_model=Dict[str, Any])
async def delete_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to delete"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Delete a challenge if it is not active."""
    try:
        success = await challenge_service.delete_challenge(challenge_id)
        if success:
            return {"message": "Challenge deleted successfully"}
        raise HTTPException(status_code=400, detail="Challenge cannot be deleted")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{challenge_id}/join", response_model=Dict[str, Any])
async def join_challenge(
        participation_data: ChallengeParticipationCreate,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Join a challenge."""
    try:
        participation, challenge = await challenge_service.join_challenge(participation_data)
        return {"message": "User joined challenge successfully", "challenge": challenge}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{challenge_id}/leave", response_model=Dict[str, Any])
async def leave_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to leave"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Leave a challenge."""
    try:
        result = await challenge_service.leave_challenge(challenge_id, str(current_user.id))
        if result:
            return {"message": "User left challenge successfully", "result": result}
        else:
            return {"message": "User was not in challenge", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{challenge_id}/leaderboard", response_model=List[Dict[str, Any]])
async def get_challenge_leaderboard(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        limit: int = Query(10, description="Number of top participants to return"),
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get the leaderboard for a challenge."""
    return await challenge_service.get_challenge_leaderboard(challenge_id, limit=limit)


@router.put("/{challenge_id}/status", response_model=Challenge)
async def update_challenge_status(
        status: ChallengeStatus,
        challenge_id: str = Path(..., description="The ID of the challenge"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Manually update a challenge's status."""
    challenge = await challenge_service.update_challenge_status(challenge_id, status)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.get("/{challenge_id}/participants", response_model=List[Dict[str, Any]])
async def get_challenge_participants(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        skip: int = Query(0, description="Skip N participants"),
        limit: int = Query(10, description="Limit number of participants"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get participants in a challenge."""
    return await challenge_service.get_challenge_participants(challenge_id, skip, limit)


@router.patch("/{challenge_id}/participants/{user_id}", response_model=Dict[str, Any])
async def update_participant_stats(
        challenge_id: str,
        user_id: str,
        update_data: ChallengeParticipationUpdate,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Update stats or role of a participant."""
    updated = await challenge_service.update_participant_stats(challenge_id, user_id, update_data)
    return {"message": "Participant updated successfully", "participant": updated}


@router.post("/{challenge_id}/publish", response_model=Challenge)
async def publish_challenge(
        challenge_id: str,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Publish a challenge."""
    challenge = await challenge_service.publish_challenge(challenge_id)
    return challenge


@router.post("/{challenge_id}/unpublish", response_model=Challenge)
async def unpublish_challenge(
        challenge_id: str,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Unpublish a challenge."""
    challenge = await challenge_service.unpublish_challenge(challenge_id)
    return challenge
