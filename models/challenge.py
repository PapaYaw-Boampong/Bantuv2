import uuid
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum

if TYPE_CHECKING:
    from models import User, ChallengeReward


class ChallengeStatus(str, PyEnum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"


class EventType(str, PyEnum):
    DATA_COLLECTION = "data_collection"
    SAMPLE_REVIEW = "data_review"


class TaskType(str, PyEnum):
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    ANNOTATION = "annotation"


class EventCategory(str, PyEnum):
    COMPETITION = "time_based_competition"  # Timed, ranked events
    BOUNTY = "bounty"  # Task-based


# ===================== EVENTS TABLE =====================
class Challenge(SQLModel, table=True):
    __tablename__ = "challenge"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    challenge_name: str
    description: Optional[str] = None
    event_type: EventType
    task_type: TaskType
    event_category: EventCategory
    start_date: datetime
    end_date: datetime
    status: ChallengeStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = Field(default=True)
    is_published: bool = Field(default=False)

    # Statistics
    participant_count: int = Field(default=0)
    contribution_count: int = Field(default=0)

    # Relationship
    participants: List["ChallengeParticipation"] = Relationship(
        back_populates="event",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    rewards: "ChallengeReward" = Relationship(
        back_populates="challenge", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== EVENT PARTICIPATION TABLE =====================
class ChallengeParticipation(SQLModel, table=True):
    __tablename__ = "challenge_participation"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    event_id: uuid.UUID = Field(foreign_key="challenge.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")

    # Statistics
    total_hours_speech: int = Field(default=0)
    total_sentences_translated: int = Field(default=0)
    total_tokens_produced: int = Field(default=0)
    total_points: int = Field(default=0)
    acceptance_rate: float = Field(default=0.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(
        back_populates="events",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    event: "Challenge" = Relationship(
        back_populates="participants",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
