from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict
from datetime import datetime

from models.user import User
from models.language import Language
from models.vote import Vote


# ===================== CONTRIBUTIONS TABLE =====================
class Contribution(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id")
    data_id: str = Field(foreign_key="data_store.id")

    contribution_type: str  # "translation" or "transcription"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = Field(default=False)  # New field to indicate if the contribution is flagged
    active: bool = Field(default=True)  # New field to indicate if the contribution is active

    # Relationships
    user: "User" = Relationship(back_populates="contributions")
    language: "Language" = Relationship(back_populates="contributions")
    votes: List["Vote"] = Relationship(back_populates="contribution")

    # New Relationship for flagged contributions
    flagged_audio: List["FlaggedAudio"] = Relationship(back_populates="contribution")


# ===================== FLAGGED AUDIO TABLE =====================
class FlaggedAudio(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id")
    contribution_id: str = Field(foreign_key="contribution.id")
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship()
    contribution: "Contribution" = Relationship(back_populates="flagged_audio")