from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from pydantic import UUID4
from api.v1.deps import get_session, get_current_active_user, get_current_superuser
from models.user import User

from models.rewards import (
    Milestone, UserMilestone,
    ChallengeReward, UserChallengeReward, RewardType,
)
from schemas.rewards import (
    MilestoneCreate, MilestoneUpdate, MilestoneResponse,
    UserMilestoneCreate, UserMilestoneResponse,
    ChallengeRewardCreate,
    UserChallengeRewardCreate,
    GetRewards,
)
from services.reward_service import RewardsService

router = APIRouter()


# Milestone endpoints
@router.post("/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
        milestone_data: MilestoneCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
):
    rewards_service = RewardsService(db)
    try:
        milestone = await rewards_service.create_milestone(milestone_data)
        return milestone
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not create milestone: {str(e)}"
        )


@router.get("/milestones", response_model=List[MilestoneResponse])
async def list_milestones(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    """List all milestones"""
    rewards_service = RewardsService(db)
    milestones = await rewards_service.list_milestones()
    return milestones


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
        milestone_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    """Get a specific milestone by ID"""
    rewards_service = RewardsService(db)
    milestone = await rewards_service.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    return milestone


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
        milestone_id: str,
        milestone_data: MilestoneUpdate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
):
    """Update a milestone (admin only)"""
    rewards_service = RewardsService(db)
    updated_milestone = await rewards_service.update_milestone(milestone_id, milestone_data)
    if not updated_milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    return updated_milestone


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(
        milestone_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
):
    """Delete a milestone (admin only)"""
    rewards_service = RewardsService(db)
    success = await rewards_service.delete_milestone(UUID4(milestone_id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    return None


# User Milestone endpoints
@router.post("/user-milestones/", response_model=UserMilestoneResponse, status_code=status.HTTP_201_CREATED)
async def award_milestone(
        user_milestone_data: UserMilestoneCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_superuser)
):
    """Award a milestone to a user (admin only)"""

    rewards_service = RewardsService(db)
    try:
        user_milestone = await rewards_service.award_milestone(user_milestone_data)
        return user_milestone
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not award milestone: {str(e)}"
        )


@router.get("/user-milestones/me", response_model=List[UserMilestoneResponse])
async def get_my_milestones(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    """Get all milestones awarded to the current user"""
    rewards_service = RewardsService(db)
    user_milestones = await rewards_service.get_user_milestones(str(current_user.id))
    return user_milestones


@router.get("/user-milestones/{user_id}", response_model=List[UserMilestoneResponse])
async def get_user_milestones(
        user_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    """Get all milestones awarded to a specific user (admin only)"""
    if current_user.role < 2 and str(current_user.id) != user_id:  # Only admins or the user themselves can view
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    rewards_service = RewardsService(db)
    user_milestones = await rewards_service.get_user_milestones(user_id)
    return user_milestones


# Create a challenge reward
@router.post("/rewards", response_model=ChallengeReward)
async def create_challenge_reward(
        reward_data: ChallengeRewardCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    rewards_service = RewardsService(db)
    reward = await rewards_service.create_challenge_reward(reward_data)
    return reward


# Get a challenge reward
@router.get("/rewards/{reward_id}", response_model=ChallengeReward)
async def get_challenge_reward(
        reward_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    rewards_service = RewardsService(db)
    reward = await rewards_service.get_challenge_reward(reward_id)
    if not reward:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    return reward


# List challenge rewards
@router.get("/rewards", response_model=List[ChallengeReward])
async def list_challenge_rewards(
        query_params: GetRewards,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    rewards_service = RewardsService(db)
    rewards = await rewards_service.list_challenge_rewards(query_params)
    return rewards


# Award challenge reward
@router.post("/users/{user_id}/rewards", response_model=UserChallengeReward)
async def award_challenge_reward(
        user_id: str,
        award_data: UserChallengeRewardCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    rewards_service = RewardsService(db)
    award = await rewards_service.award_challenge_reward(award_data)
    return award


# Get challenge rewards by user
@router.get("/users/{user_id}/rewards", response_model=List[UserChallengeReward])
async def get_user_challenge_rewards(
        user_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    rewards_service = RewardsService(db)
    rewards = await rewards_service.get_user_challenge_rewards(user_id)
    return rewards


# Get challenge rewards by challenge
@router.get("/challenges/{challenge_id}/rewards", response_model=List[UserChallengeReward])
async def get_challenge_rewards_by_challenge(
        challenge_id: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_active_user)
):
    rewards_service = RewardsService(db)
    rewards = await rewards_service.get_challenge_rewards_by_challenge(challenge_id)
    return rewards
