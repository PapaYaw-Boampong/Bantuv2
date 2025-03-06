from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

from contribution import Contribution  # Importing related models
from vote import Vote
from event import EventParticipation
from language import UserLanguage
from contribution import FlaggedAudio


# ===================== USERS TABLE =====================
class User(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    name: str
    email: str = Field(unique=True, index=True)
    country: str
    native_language: str
    last_visited: Optional[datetime] = None

    # Relationships
    contributions: List["Contribution"] = Relationship(back_populates="user")
    votes: List["Vote"] = Relationship(back_populates="user")
    events: List["EventParticipation"] = Relationship(back_populates="user")
    user_languages: List["UserLanguage"] = Relationship(back_populates="user")
    # ✅ New Relationship for Flagged Audio
    flagged_audios: List["FlaggedAudio"] = Relationship(back_populates="user")
