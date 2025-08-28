from sqlmodel import SQLModel, Field, Relationship, Column, JSON, DateTime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
import uuid

if TYPE_CHECKING:
    from models import User, Challenge


# Enum types
class RewardType(str, Enum):
    CASH = "cash"
    BADGE = "badge"
    RANK = "SWAG"


class RewardDistributionType(str, Enum):
    FIXED = "fixed"  # Each winner gets a specific amount
    TIERED = "tiered"  # First place gets more, etc.


# Rewards

class Milestone(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    name: str
    description: Optional[str] = None
    reward_type: RewardType  # badge, points, perk
    reward_value: dict = Field(sa_column=Column(JSON))
    required_actions: int = Field(ge=0)  # Number of actions needed to unlock

    milestones: List["UserMilestone"] = Relationship(
        back_populates="milestone",
    )


class UserMilestone(SQLModel, table=True):
    __tablename__ = "user_milestone"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    milestone_id: uuid.UUID = Field(foreign_key="milestone.id")
    achieved_at: datetime  = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user: "User" = Relationship(back_populates="user_milestones", sa_relationship_kwargs={"lazy": "selectin"})
    milestone: "Milestone" = Relationship(back_populates="milestones", sa_relationship_kwargs={"lazy": "selectin"})


class ChallengeReward(SQLModel, table=True):
    __tablename__ = "challenge_reward"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)

    reward_type: RewardType  # Cash, badge, leaderboard rank
    reward_distribution_type: RewardDistributionType = Field(default=RewardDistributionType.FIXED)  # Fixed, percentage, tiered
    reward_threshold: int = Field(default=1)  # Minimum number of participants to distribute rewards
    participant_threshold: int = Field(default=1)  # Maximum number of participants to distribute rewards to
    reward_value: dict = Field(sa_column=Column(JSON))
    description: str = Field(nullable=True)
    created_at: datetime  = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # New Relationship to UserChallengeReward
    user_rewards: List["UserChallengeReward"] = Relationship(
        back_populates="reward", sa_relationship_kwargs={"lazy": "selectin"}
    )

    challenge: "Challenge" = Relationship(
        back_populates="reward",
        sa_relationship_kwargs={"lazy": "selectin", "uselist": False,  # One-to-one relationship
                                "single_parent": True # Ensures the ChallengeReward is only linked to a single Challenge
                                }
    )


class UserChallengeReward(SQLModel, table=True):
    __tablename__ = "user_challenge_reward"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    reward_id: uuid.UUID = Field(foreign_key="challenge_reward.id")
    rank: int = Field(default=1)
    awarded_at: datetime  = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    claimed: bool = Field(default=False)

    reward: "ChallengeReward" = Relationship(back_populates="user_rewards")
    user: "User" = Relationship(back_populates="challenge_reward")
