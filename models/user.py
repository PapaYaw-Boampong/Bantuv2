import uuid

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


# from models.contribution import TranslationContribution, TranscriptionContribution
# from models.challenge import ChallengeParticipation
# from models.language import UserLanguage


# ===================== USERS TABLE =====================
class User(SQLModel, table=True):
    __tablename__ = "user"
    id:  uuid.UUID = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )

    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

    is_active: bool = Field(default=True)
    recently_active: bool = Field(default=True)  # active within the last 10 days
    role: int = Field(default=1)  # 1: user, 2: admin, 3: superadmin

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Reputation metrics
    contribution_count: int = Field(default=0)
    accepted_contributions: int = Field(default=0)
    reputation_score: float = Field(default=0.0)

    # Statistics
    total_hours_speech: int = Field(default=0)
    total_sentences_translated: int = Field(default=0)
    total_tokens_produced: int = Field(default=0)
    total_points: int = Field(default=0)

    # Relationships
    transcription_contributions: List["TranscriptionContribution"] = Relationship(back_populates="user")
    translation_contributions: List["TranslationContribution"] = Relationship(back_populates="user")

    transcription_circulation_records: List["TranscriptionCirculationRecord"] = Relationship(back_populates="user")
    translation_circulation_records: List["TranslationCirculationRecord"] = Relationship(back_populates="user")

    events: List["ChallengeParticipation"] = Relationship(back_populates="user")
    user_languages: List["UserLanguage"] = Relationship(back_populates="user")
