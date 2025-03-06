from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict
from datetime import datetime

from user import User
from language import Language
from vote import Vote


class DataSample(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    language_id: str = Field(foreign_key="language.id")

    sample_type: str  # "speech", "transcription", or "translation"
    content: str
    audio_url: Optional[str] = None  # Used only if the sample is an audio file

    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    # Relationships
    user: "User" = Relationship(back_populates="data_samples")
    language: "Language" = Relationship(back_populates="data_samples")
    votes: List["Vote"] = Relationship(back_populates="data_sample")  # Votes on the sample

