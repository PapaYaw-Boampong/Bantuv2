import uuid

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

from contribution import TranslationContribution, TranscriptionContribution  # Importing related models
from challenge import ChallengeParticipation
from language import UserLanguage


# ===================== USERS TABLE =====================
class User(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )

    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str

    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
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
    events: List["ChallengeParticipation"] = Relationship(back_populates="user")
    user_languages: List["UserLanguage"] = Relationship(back_populates="user")


