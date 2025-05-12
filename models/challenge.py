import uuid
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum

if TYPE_CHECKING:
    from models import User, ChallengeReward, Language, EvaluationInstance


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
    language_id: uuid.UUID = Field(foreign_key="language.id")

    creator_id: uuid.UUID = Field(foreign_key="user.id")

    challenge_reward_id: uuid.UUID = Field(foreign_key="challenge_reward.id")

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

    # Add progress tracking
    completion_percent: float = Field(default=0.0)

    # Statistics
    participant_count: int = Field(default=0)
    contribution_count: int = Field(default=0)

    # Relationships

    # Relationships
    user: Optional["User"]= Relationship(
        back_populates="challenges",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    participants: List["ChallengeParticipation"] = Relationship(
        back_populates="challenge",
        sa_relationship_kwargs={"cascade": "all, delete", "lazy": "selectin"}
    )

    reward: "ChallengeReward" = Relationship(
        back_populates="challenge",
        sa_relationship_kwargs={
            "lazy": "selectin",
        }
    )

    language: "Language" = Relationship(
        back_populates="challenges", sa_relationship_kwargs={"lazy": "selectin"}
    )

    rules: List["ChallengeRule"] = Relationship(
        back_populates="challenge",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )

    evaluation_instances: List["EvaluationInstance"] = Relationship(
        back_populates="challenge",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
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
    total_annotation_tokens: int = Field(default=0)
    total_points: int = Field(default=0)

    # Reputation Metrics
    contribution_count: int = Field(default=0)
    accepted_contributions: int = Field(default=0)
    contribution_acceptance_score: float = Field(default=0.0)

    evaluation_count: int = Field(default=0)
    accepted_evaluations: int = Field(default=0)
    evaluation_acceptance_score: float = Field(default=0.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Score Counters
    eval_score_counter: int = Field(default=0)
    contribution_score_counter: int = Field(default=0)

    # Relationships
    user: "User" = Relationship(
        back_populates="events",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    challenge: "Challenge" = Relationship(
        back_populates="participants",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete"}
    )


class ChallengeRule(SQLModel, table=True):
    __tablename__ = "challenge_rules"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    challenge_id: uuid.UUID = Field(
        foreign_key="challenge.id",
        index=True
    )
    rule_title: str = Field(max_length=100)
    rule_description: str
    is_required: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    challenge: "Challenge" = Relationship(
        back_populates="rules",
        sa_relationship_kwargs={
            "cascade": "all, delete",  # Critical for automatic deletion
            "passive_deletes": True
        }
    )
