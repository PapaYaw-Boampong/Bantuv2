from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict
from datetime import datetime

from user import User
from language import Language


# ===================== TRANSCRIPTION SAMPLE TABLE =====================
class TranscriptionSample(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    language_id: str = Field(foreign_key="language.id")

    audio_urls: List[Dict[str, str]] = Field(sa_column_kwargs={
        "type": "json"})  # Stores multiple validated speech samples of the audio URLsaudio_url: str  # Stores the

    # URL/path of the audio file
    transcription_text: str  # Stores the transcribed text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    # Relationships
    language: "Language" = Relationship(back_populates="transcriptions")


# ===================== TRANSLATION SAMPLE TABLE =====================
class TranslationSample(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    language_id: str = Field(foreign_key="language.id")

    original_text: str  # The original text in English
    translated_text: str  # The translated version of the text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validated: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    # Relationships
    language: "Language" = Relationship(back_populates="translations")
