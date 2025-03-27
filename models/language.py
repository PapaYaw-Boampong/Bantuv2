import uuid

from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional


# from models.user import User
# from models.contribution import TranscriptionContribution, TranslationContribution
#

# ===================== LANGUAGES TABLE =====================
class Language(SQLModel, table=True):
    __tablename__ = "language"
    id: uuid.UUID = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )

    name: str
    description: Optional[str] = None
    code: str = Field(
        index=True, unique=True
    )  # ISO code

    # Statistics
    contribution_count: int = Field(default=0)
    contributor_count: int = Field(default=0)

    # Relationships
    user_languages: List["UserLanguage"] = Relationship(back_populates="language")

    transcriptions: List["TranscriptionSample"] = Relationship(back_populates="language")

    translations: List["TranslationSample"] = Relationship(back_populates="language")


class UserLanguage(SQLModel, table=True):
    __tablename__ = "user_language"
    id: uuid.UUID = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")
    total_hours_speech: Optional[int] = 0
    total_sentences_translated: Optional[int] = 0

    # Relationships
    user: "User" = Relationship(back_populates="user_languages")
    language: "Language" = Relationship(back_populates="user_languages")
