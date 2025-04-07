from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from models import User, Challenge


# Enum types

class RewardType(str, Enum):
    CASH = "cash"
    BADGE = "badge"
    RANK = "SWAG"


# Branded merchandise, swag, etc.


class RewardDistributionType(str, Enum):
    FIXED = "fixed"  # Each winner gets a specific amount
    PERCENTAGE = "percentage"  # Split based on predefined percentages
    TIERED = "tiered"  # First place gets more, etc.


# Rewards

class Milestone(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str
    description: Optional[str] = None
    reward_type: RewardType  # badge, points, perk
    reward_value: str  # JSON or simple string (e.g., {"badge": "Pro Translator"})
    required_actions: int = Field(ge=0)  # Number of actions needed to unlock

    milestones: List["UserMilestone"] = Relationship(
        back_populates="milestone",
        sa_relationship_kwargs={"lazy": "selectin"}
    )


class UserMilestone(SQLModel, table=True):
    __tablename__ = "user_milestone"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    milestone_id: uuid.UUID = Field(foreign_key="milestone.id")
    achieved_at: datetime

    user: "User" = Relationship(back_populates="user_milestones", sa_relationship_kwargs={"lazy": "selectin"})
    milestone: "Milestone" = Relationship(back_populates="milestones", sa_relationship_kwargs={"lazy": "selectin"})


class ChallengeReward(SQLModel, table=True):
    __tablename__ = "challenge_reward"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    challenge_id: uuid.UUID = Field(foreign_key="challenge.id")

    reward_type: RewardType  # Cash, badge, leaderboard rank
    reward_value: str  # JSON for flexible storage (e.g., {"points": "500"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    claimed: bool = Field(default=False)

    # Relationship
    distributions: List["RewardDistribution"] = Relationship(
        back_populates="reward", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # New Relationship to UserChallengeReward
    user_rewards: List["UserChallengeReward"] = Relationship(
        back_populates="reward", sa_relationship_kwargs={"lazy": "selectin"}
    )

    challenge: "Challenge" = Relationship(back_populates="rewards")


class RewardDistribution(SQLModel, table=True):
    __tablename__ = "reward_distribution"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    reward_id: uuid.UUID = Field(foreign_key="challenge_reward.id")

    distribution_type: RewardDistributionType
    allocation: str  # JSON field for custom splits (e.g., {"1st": 50, "2nd": 30, "3rd": 20})

    reward: "ChallengeReward" = Relationship(back_populates="distributions")


class UserChallengeReward(SQLModel, table=True):
    __tablename__ = "user_challenge_reward"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    reward_id: uuid.UUID = Field(foreign_key="challenge_reward.id")
    awarded_at: datetime = Field(default_factory=datetime.utcnow)
    claimed: bool = Field(default=False)

    reward: "ChallengeReward" = Relationship(back_populates="user_rewards")
    user: "User" = Relationship(back_populates="challenge_reward")
