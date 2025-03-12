import uuid

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum
from user import User


class EventType(str, PyEnum):
    TRANSCRIPTION_CHALLENGE = "transcription_challenge"
    TRANSLATION_SPRINT = "translation_challenge"
    CORRECTION_MARATHON = "correction_marathon"


# ===================== EVENTS TABLE =====================
class Challenge(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )

    challenge_name: str
    description: Optional[str] = None
    EventType: EventType
    start_date: datetime
    end_date: datetime
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Target metrics
    target_contribution_count: Optional[int] = None

    # Statistics
    participant_count: int = Field(default=0)
    contribution_count: int = Field(default=0)

    # Relationship
    participants: List["ChallengeParticipation"] = Relationship(back_populates="event")


# ===================== EVENT PARTICIPATION TABLE =====================
class ChallengeParticipation(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )

    event_id: str = Field(foreign_key="event.id")
    user_id: str = Field(foreign_key="user.id")

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
    user: "User" = Relationship(back_populates="events")
    event: "Challenge" = Relationship(back_populates="participants")
