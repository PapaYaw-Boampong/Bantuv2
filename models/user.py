import uuid
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

if TYPE_CHECKING:
    from models import (
        TranscriptionContribution, TranslationContribution, AnnotationContribution,
        TranscriptionCirculationRecord, TranslationCirculationRecord, AnnotationCirculationRecord,
        UserLanguage, ChallengeParticipation, RefreshToken,
        UserMilestone, UserChallengeReward
    )


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

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    transcription_contributions: List["TranscriptionContribution"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    translation_contributions: List["TranslationContribution"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    annotation_contributions: List["AnnotationContribution"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    transcription_circulation_records: List["TranscriptionCirculationRecord"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    translation_circulation_records: List["TranslationCirculationRecord"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    annotation_circulation_records: List["AnnotationCirculationRecord"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    events: List["ChallengeParticipation"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )

    user_languages: List["UserLanguage"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )

    refresh_tokens: List["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    challenge_reward: List["UserChallengeReward"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )

    user_milestones: List["UserMilestone"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )

    statistics: Optional["UserStatistics"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )


class UserStatistics(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", unique=True)

    # Translation Reputation Metrics
    translation_contribution_count: int = Field(default=0)
    translation_accepted_contributions: int = Field(default=0)
    translation_reputation_score: float = Field(default=0.0)

    # Transcription Reputation Metrics
    transcription_contribution_count: int = Field(default=0)
    transcription_accepted_contributions: int = Field(default=0)
    transcription_reputation_score: float = Field(default=0.0)

    # Activity Statistics
    total_hours_speech: int = Field(default=0)
    total_sentences_translated: int = Field(default=0)
    total_tokens_produced: int = Field(default=0)

    # Last Updated
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship with User
    user: "User" = Relationship(back_populates="statistics")
