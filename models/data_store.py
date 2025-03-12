import uuid
from sqlmodel import SQLModel, Field, Relationship
from typing import List, Dict
from datetime import datetime
from typing import Optional

from user import User
from language import Language
from contribution import TranscriptionContribution, TranslationContribution


# ===================== TRANSCRIPTION SAMPLE TABLE =====================
class TranscriptionSample(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True, index=True
    )

    language_id: str = Field(foreign_key="language.id")

    audio_urls: List[Dict[str, str]] = Field(sa_column_kwargs={
        "type": "json"})  # Stores multiple validated speech samples of the audio URLsaudio_url: str  # Stores the
    transcription_text: str  # Stores the transcribed text
    # translation_text: str  # Stores the translated text
    category: Optional[str] = None  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    # Relationships
    language: "Language" = Relationship(back_populates="transcriptions")
    contributions: List["TranscriptionContribution"] = Relationship(back_populates="seed_data")


# ===================== TRANSLATION SAMPLE TABLE =====================
class TranslationSample(SQLModel, table=True):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
        , primary_key=True,
        index=True
    )
    language_id: str = Field(foreign_key="language.id")

    original_text: str  # The original text in English
    translated_text: str  # The translated version of the text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    # Relationships
    language: "Language" = Relationship(back_populates="translations")
    contributions: List["TranslationContribution"] = Relationship(back_populates="seed_data")
