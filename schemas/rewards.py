from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
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
    id: str
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
    achieved_at: datetime = datetime.utcnow()


class UserMilestoneResponse(BaseModel):
    id: str
    user_id: str
    milestone_id: str
    achieved_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Challenge Reward schemas
class ChallengeRewardCreate(BaseModel):
    reward_type: RewardType
    reward_distribution_type: RewardDistributionType
    reward_value: dict


class ChallengeRewardUpdate(BaseModel):
    reward_type: Optional[RewardType] = None
    reward_value: Optional[str] = None


class ChallengeRewardResponse(BaseModel):
    id: str
    reward_type: RewardType
    reward_distribution_type: RewardDistributionType
    reward_value: dict
    created_at: datetime
    claimed: bool = False

    model_config = ConfigDict(from_attributes=True)


# User Challenge Reward schemas
class UserChallengeRewardCreate(BaseModel):
    user_id: str
    reward_id: str
    challenge_id: str
    rank: int
    awarded_at: datetime = datetime.utcnow()


class UserChallengeRewardResponse(BaseModel):
    id: str
    user_id: str
    reward_id: str
    rank: int
    amount: Optional[float] = None # Derived from reward_value
    claimed: bool = False
    challenge_id: str
    awarded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Get rewards queries
class GetRewards(BaseModel):
    reward_type: Optional[RewardType] = None
    skip: int = 0
    limit: int = 100


