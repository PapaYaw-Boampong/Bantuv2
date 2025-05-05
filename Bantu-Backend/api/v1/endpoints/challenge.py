import uuid
from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from database import get_session
from models.challenge import Challenge, ChallengeStatus, EventType, TaskType, EventCategory
from models.user import User
from schemas.challenge import (
    SaveChallengeData,
    SaveChallengeResponse,
    ChallengeUpdate,
    ChallengeParticipationCreate,
    ParticipationUpdate,
    GetChallenges,
    UserChallengeFilter
)
from services.challenge_service import ChallengeService
from services.reward_service import RewardsService
from api.v1.deps import get_current_active_user, get_current_superuser

router = APIRouter()


# Dependency
def get_challenge_service(db: AsyncSession = Depends(get_session)):
    return ChallengeService(db)


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def get_reward_service(db: AsyncSession = Depends(get_session)):
    return RewardsService(db)


# Static Routes (defined first to take precedence)
@router.post("/save", response_model=SaveChallengeResponse)
async def save_challenge(
        save_data: SaveChallengeData,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        reward_service: RewardsService = Depends(get_reward_service),
        current_user: User = Depends(get_current_active_user)
):
    """Create a new challenge."""

    challenge_data = save_data.challenge_data
    rules_data = save_data.challenge_rules
    challenge_reward_data = save_data.challenge_reward

    if not challenge_data:
        raise HTTPException(status_code=400, detail="Challenge data must be provided.")

    challenge_data.creator_id = current_user.id

    # Save or update challenge reward if provided
    if challenge_reward_data:
        if not challenge_reward_data.id:
            reward = await reward_service.create_challenge_reward(challenge_reward_data)
        elif is_valid_uuid(str(challenge_reward_data.id)):
            reward = await reward_service.update_challenge_reward(
                uuid.UUID(challenge_reward_data.id),
                challenge_reward_data
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid reward ID format")

        challenge_data.challenge_reward_id = reward.id
    else:
        raise HTTPException(status_code=400, detail="Challenge reward data must be provided.")

    if challenge_data.id is None:
        challenge = await challenge_service.create_challenge(challenge_data, current_user.id)
        challenge_data.id = challenge.id

    # Save or update challenge
    challenge = await challenge_service.update_challenge(
        challenge_data,
        challenge_data.id,
        challenge_data.creator_id)

    # Save or update challenge rules if provided
    rules_data = []

    if rules_data:
        for rule in rules_data:
            if rule.id == "":
                await challenge_service.rule_repository.add_rule(challenge.id, rule)
            elif is_valid_uuid(rule.id):
                await challenge_service.rule_repository.update_rule(rule.id, rule)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid rule ID: {rule.id}")
        rules_data = await challenge_service.rule_repository.get_rules(challenge.id)

    return SaveChallengeResponse(challenge=challenge, reward=reward, rules=rules_data)


@router.get("/mystuff", response_model=List[Challenge])
async def get_my_challenges(
        status: Optional[str] = Query(None),
        event_type: Optional[EventType] = Query(None),
        task_type: Optional[TaskType] = Query(None),
        event_category: Optional[EventCategory] = Query(None),
        is_public: Optional[bool] = Query(None),
        is_published: Optional[bool] = Query(None),
        skip: Optional[int] = 0,
        limit: Optional[int] = 100,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user),
):
    # Manual mapping for custom terms like "ongoing"

    # status_map = {
    #     "active": ChallengeStatus.ACTIVE,
    #     "upcoming": ChallengeStatus.UPCOMING,
    #     "completed": ChallengeStatus.COMPLETED,
    #     None: None
    # }
    # task_type_map = {
    #     "transcription": TaskType.TRANSCRIPTION,
    #     "translation": TaskType.TRANSLATION,
    #     "annotation": TaskType.ANNOTATION,
    #     None: None
    # }
    #
    # event_category_map = {
    #     "time_based_competition": EventCategory.COMPETITION,
    #     "bounty": EventCategory.BOUNTY,
    #     None: None
    # }
    #
    # event_type_map = {
    #     "data_collection": EventType.DATA_COLLECTION,
    #     "data_review": EventType.SAMPLE_REVIEW,
    #     None: None
    # }

    query_params = GetChallenges(
        status=status,
        event_type=event_type,
        task_type=task_type,
        event_category=event_category,
        is_public=is_public,
        is_published=is_published,
        skip=skip,
        limit=limit
    )

    return await challenge_service.list_challenges(query_params, creator_id=current_user.id)


@router.get("/all", response_model=List[Challenge])
async def get_challenges(
        query_params: GetChallenges = Depends(),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get all challenges with filters and pagination."""
    return await challenge_service.list_challenges(query_params)


@router.get("/participating", response_model=List[Challenge])
async def get_challenges_participating(
        query_params: UserChallengeFilter = Depends(),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)

):
    """Get all challenges with filters and pagination."""
    return await challenge_service.get_user_challenges(user_id=current_user.id, filters=query_params)


@router.get("/single/{challenge_id}", response_model=Challenge)
async def get_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to get"),
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get a specific challenge by ID."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")
    challenge = await challenge_service.get_challenge(challenge_uuid)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.get("/detailed/{challenge_id}", response_model=SaveChallengeResponse)
async def get_detailed_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to get"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user),
        reward_service: RewardsService = Depends(get_reward_service)
):
    """Get a specific challenge by ID."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")
    challenge = await challenge_service.get_challenge(challenge_uuid)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    rules = await challenge_service.rule_repository.get_rules(challenge.id)
    reward = await reward_service.get_challenge_reward(challenge.challenge_reward_id)

    return SaveChallengeResponse(challenge=challenge, reward=reward, rules=rules)


@router.put("/update/{challenge_id}", response_model=Challenge)
async def update_challenge(
        challenge_data: ChallengeUpdate,
        challenge_id: str = Path(..., description="The ID of the challenge to update"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Update a challenge's information."""

    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")

    challenge = await challenge_service.update_challenge(challenge_data)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.delete("/delete/{challenge_id}", response_model=Dict[str, Any])
async def delete_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to delete"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Delete a challenge if it is not active."""

    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")

    try:
        success = await challenge_service.delete_challenge(challenge_uuid)
        if success:
            return {"message": "Challenge deleted successfully"}
        raise HTTPException(status_code=400, detail="Challenge cannot be deleted")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/join/{challenge_id}", response_model=Dict[str, Any])
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


@router.post("/leave/{challenge_id}", response_model=Dict[str, Any])
async def leave_challenge(
        challenge_id: str = Path(..., description="The ID of the challenge to leave"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Leave a challenge."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")

    try:
        result = await challenge_service.leave_challenge(challenge_uuid, current_user.id)
        if result:
            return {"message": "User left challenge successfully", "result": result}
        else:
            return {"message": "User was not in challenge", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/leaderboard/{challenge_id}", response_model=List[Dict[str, Any]])
async def get_challenge_leaderboard(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        limit: int = Query(10, description="Number of top participants to return"),
        challenge_service: ChallengeService = Depends(get_challenge_service)
):
    """Get the leaderboard for a challenge."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")

    return await challenge_service.get_challenge_leaderboard(challenge_uuid, limit=limit)


@router.put("/status/{challenge_id}", response_model=Challenge)
async def update_challenge_status(
        status: ChallengeStatus,
        challenge_id: str = Path(..., description="The ID of the challenge"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Manually update a challenge's status."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")
    challenge = await challenge_service.update_challenge_status(challenge_uuid, status)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"Challenge with ID {challenge_id} not found")
    return challenge


@router.get("/participants/{challenge_id}/", response_model=List[Dict[str, Any]])
async def get_challenge_participants(
        challenge_id: str = Path(..., description="The ID of the challenge"),
        skip: int = Query(0, description="Skip N participants"),
        limit: int = Query(10, description="Limit number of participants"),
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get participants in a challenge."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")
    return await challenge_service.get_challenge_participants(challenge_uuid, skip, limit)


@router.patch("/participants/{challenge_id}/{user_id}", response_model=Dict[str, Any])
async def update_participant_stats(
        challenge_id: str,
        user_id: str,
        update_data: ParticipationUpdate,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    try:
        challenge_uuid = uuid.UUID(challenge_id)
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")
    """Update stats or role of a participant."""
    updated = await challenge_service.update_participation_stats(
        challenge_uuid,
        user_uuid,
        update_data)
    return {"message": "Participant updated successfully", "participant": updated}


@router.post("/publish/{challenge_id}", response_model=Challenge)
async def publish_challenge(
        challenge_id: str,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Publish a challenge."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")
    challenge = await challenge_service.publish_challenge(challenge_uuid)
    return challenge


@router.post("/unpublish/{challenge_id}", response_model=Challenge)
async def unpublish_challenge(
        challenge_id: str,
        challenge_service: ChallengeService = Depends(get_challenge_service),
        current_user: User = Depends(get_current_superuser)
):
    """Unpublish a challenge."""
    try:
        challenge_uuid = uuid.UUID(challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid challenge ID format")

    challenge = await challenge_service.unpublish_challenge(challenge_uuid)
    return challenge
