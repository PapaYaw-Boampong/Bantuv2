from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, UUID4
from models.rewards import RewardType, RewardDistributionType


# Milestone schemas
class MilestoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    reward_type: RewardType
    reward_value: dict
    required_actions: int


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    reward_type: Optional[RewardType] = None
    reward_value: Optional[dict] = None
    required_actions: Optional[int] = None


class MilestoneResponse(BaseModel):
    id: UUID4
    name: str
    description: Optional[str] = None
    reward_type: RewardType
    reward_value: dict
    required_actions: int

    model_config = ConfigDict(from_attributes=True)


# User Milestone schemas
class UserMilestoneCreate(BaseModel):
    user_id: str
    milestone_id: str


class UserMilestoneResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    milestone_id: UUID4

    model_config = ConfigDict(from_attributes=True)


# Challenge Reward schemas
class ChallengeRewardCreate(BaseModel):
    reward_type: RewardType
    reward_distribution_type: RewardDistributionType
    reward_value: dict


class ChallengeRewardUpdate(BaseModel):
    id: Optional[UUID4] = None
    reward_type: Optional[RewardType] = None
    reward_distribution_type: Optional[RewardDistributionType] = None
    reward_value: Optional[dict] = None


class ChallengeReward(BaseModel):
    id: UUID4
    reward_type: RewardType
    reward_distribution_type: RewardDistributionType
    reward_value: dict
    created_at: datetime
    claimed: bool = False

    model_config = ConfigDict(from_attributes=True)


# User Challenge Reward schemas
class UserChallengeRewardCreate(BaseModel):
    user_id: UUID4
    reward_id: UUID4
    challenge_id: UUID4
    rank: int
    awarded_at: datetime = datetime.utcnow()


class UserChallengeRewardResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    reward_id: UUID4
    rank: int
    amount: Optional[float] = None  # Derived from reward_value
    claimed: bool = False
    challenge_id: str
    awarded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Get rewards queries
class GetRewards(BaseModel):
    reward_type: Optional[RewardType] = None
    skip: int = 0
    limit: int = 100
