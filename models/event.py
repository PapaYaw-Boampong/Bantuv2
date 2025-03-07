import uuid

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

from user import User


# ===================== EVENTS TABLE =====================
class Event(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    event_name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship
    participants: List["EventParticipation"] = Relationship(back_populates="event")


# ===================== EVENT PARTICIPATION TABLE =====================
class EventParticipation(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    event_id: str = Field(foreign_key="event.id")
    user_id: str = Field(foreign_key="user.id")
    total_hours_speech: int = Field(default=0)
    total_sentences_translated: int = Field(default=0)
    total_tokens_produced: int = Field(default=0)
    total_points: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(back_populates="events")
    event: "Event" = Relationship(back_populates="participants")
