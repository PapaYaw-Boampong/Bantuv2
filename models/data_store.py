import uuid
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON
from sqlalchemy import Column
from typing import List, Dict
from datetime import datetime
from typing import Optional


# from user import User
# from models.language import Language
# from models.contribution import TranscriptionContribution, TranslationContribution


# ===================== TRANSCRIPTION SAMPLE TABLE =====================
class TranscriptionSample(SQLModel, table=True):
    __tablename__ = "transcription_sample"
    id: uuid.UUID = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True, index=True
    )

    language_id: uuid.UUID = Field(foreign_key="language.id")

    # Use sqlalchemy JSON type to store list of dictionaries
    audio_urls: Optional[List[Dict[str, str]]] = Field(
        sa_column=Column(JSON),
        default=None
    )  # Stores multiple validated speech samples of the audio URLsaudio_url: str  # Stores the
    transcription_text: str  # Stores the transcribed text
    # translation_text: str  # Stores the translated text
    category: Optional[str] = None  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    sm1: int = Field(default=0)  # Stores branch 1 step
    sm2: int = Field(default=0)  # Stores branch 2 step
    sm3: int = Field(default=0)  # Stores branch 3 step

    # Relationships

    language: "Language" = Relationship(back_populates="transcriptions")
    contributions: List["TranscriptionContribution"] = Relationship(back_populates="transcription_sample")


# ===================== TRANSLATION SEED DATA TABLE =====================
class TranslationSeedData(SQLModel, table=True):
    __tablename__ = "translation_seed_data"
    """Stores the original base text (e.g., English) before translations are made in various languages"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    original_text: str  # The base text (usually English or a major language)
    category: Optional[str] = None  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when a threshold of upvotes is met

    # Relationships
    translations: List["TranslationSample"] = Relationship(back_populates="translation_seed_data")


# ===================== TRANSLATION SAMPLE TABLE =====================
class TranslationSample(SQLModel, table=True):
    __tablename__ = "translation_sample"
    """Stores validated translations of a seed across multiple languages"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    seed_data_id: uuid.UUID = Field(foreign_key="translation_seed_data.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")

    translated_text: str  # The translated version of the original text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when a threshold of upvotes is met

    sm1: int = Field(default=0)  # Stores branch 1 step
    sm2: int = Field(default=0)  # Stores branch 2 step
    sm3: int = Field(default=0)  # Stores branch 3 step

    # Relationships
    translation_seed_data: "TranslationSeedData" = Relationship(back_populates="translations")
    language: "Language" = Relationship(back_populates="translations")
    contributions: List["TranslationContribution"] = Relationship(back_populates="translation_sample")
