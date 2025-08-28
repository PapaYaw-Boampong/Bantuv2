import uuid
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, DateTime,Column
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum as PyEnum

if TYPE_CHECKING:
    from models import (
        TranscriptionContribution, TranslationContribution, AnnotationContribution,
        EvaluationStep, ChallengeParticipation, RefreshToken, Language,
        UserMilestone, UserChallengeReward, Challenge
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
    created_at: datetime =   Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime =  Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

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
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )

    events: List["ChallengeParticipation"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    # Relationships
    challenges: List["Challenge"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    user_languages: List["UserLanguage"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    refresh_tokens: List["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete"}
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

    proficiency: str = Field(default="beginner")

    ranking: int = Field(default=0)  # Ranking in the leaderboard for this language

    # Relationships
    user: "User" = Relationship(
        back_populates="user_languages"
    )
    
    language: "Language" = Relationship(
        back_populates="user_languages", sa_relationship_kwargs={}
    )

    task_stats: List["UserLanguageStats"] = Relationship(
        back_populates="user_language",
        sa_relationship_kwargs={ "cascade": "all, delete-orphan"}
    )


class UserLanguageStats(SQLModel, table=True):
    __tablename__ = "user_language_stats"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    user_language_id: uuid.UUID = Field(foreign_key="user_language.id")

    task_type: TaskType = Field(default=None)

    proficiency: float = Field(default=3.0)

    # Statistics
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

    # Score Counters
    eval_score_counter: int = Field(default=0)
    contribution_score_counter: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    user_language: "UserLanguage" = Relationship(
        back_populates="task_stats",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
