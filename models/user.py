import uuid
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum

if TYPE_CHECKING:
    from models import (
        TranscriptionContribution, TranslationContribution, AnnotationContribution,
        # TranscriptionEvaluationRecord, TranslationEvaluationRecord, AnnotationEvaluationRecord,
        # EvaluationStep, ChallengeParticipation, RefreshToken, Language,
        UserMilestone, UserChallengeReward,
    )


class TaskType(str, PyEnum):
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    ANNOTATION = "annotation"


# ===================== USERS TABLE =====================
class User(SQLModel, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    username: str = Field(index=True, unique=True)
    fullname: str = Field(index=True, unique=False)
    country: str = Field(index=True, unique=False)
    email: str = Field(index=True, unique=True)
    hashed_password: str

    is_active: bool = Field(default=True)
    recently_active: bool = Field(default=True)  # active within the last 10 days
    role: int = Field(default=1)  # 1: user, 2: admin

    # Activity Statistics
    total_hours_speech: float = Field(default=0)
    total_sentences_translated: int = Field(default=0)
    total_annotation_tokens: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    transcription_contributions: List["TranscriptionContribution"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "select"}
    )

    translation_contributions: List["TranslationContribution"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    annotation_contributions: List["AnnotationContribution"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    evaluation_steps: List["EvaluationStep"] = Relationship(
        back_populates="evaluation_branch",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )

    # transcription_evaluation_records: List["TranscriptionEvaluationRecord"] = Relationship(
    #     back_populates="user",
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    # )
    #
    # translation_evaluation_records: List["TranslationEvaluationRecord"] = Relationship(
    #     back_populates="user",
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    # )
    # annotation_evaluation_records: List["AnnotationEvaluationRecord"] = Relationship(
    #     back_populates="user",
    #     sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    # )

    events: List["ChallengeParticipation"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    user_languages: List["UserLanguage"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    refresh_tokens: List["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    challenge_reward: List["UserChallengeReward"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    user_milestones: List["UserMilestone"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )


class UserLanguage(SQLModel, table=True):
    __tablename__ = "user_language"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    user_id: uuid.UUID = Field(foreign_key="user.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")

    task_type: TaskType

    proficiency: str = Field(default="beginner")

    ranking: int = Field(default=0) # Ranking in the leaderboard for this language

    total_hours_speech: int = Field(default=0)
    total_sentences_translated: int = Field(default=0)
    total_annotation_tokens: int = Field(default=0)

    # Reputation Metrics
    contribution_count: int = Field(default=0)
    accepted_contributions: int = Field(default=0)
    contribution_acceptance_score: float = Field(default=0.0)

    evaluation_count: int = Field(default=0)
    accepted_evaluations: int = Field(default=0)
    evaluation_acceptance_score: float = Field(default=0.0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(
        back_populates="user_languages", sa_relationship_kwargs={"lazy": "selectin"}
    )
    language: "Language" = Relationship(
        back_populates="user_languages", sa_relationship_kwargs={"lazy": "selectin"}
    )
