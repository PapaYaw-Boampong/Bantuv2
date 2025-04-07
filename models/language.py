import uuid
from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import User, TranscriptionSample, TranslationSample, AnnotationSample


# ===================== LANGUAGES TABLE =====================
class Language(SQLModel, table=True):
    __tablename__ = "language"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    name: str
    description: Optional[str] = Field(default=None, nullable=True)

    code: str = Field(
        index=True, unique=True
    )  # ISO code

    # Statistics
    contribution_count: int = Field(default=0)
    contributor_count: int = Field(default=0)

    # Relationships
    user_languages: List["UserLanguage"] = Relationship(
        back_populates="language", sa_relationship_kwargs={"lazy": "selectin"}
    )

    transcriptions: List["TranscriptionSample"] = Relationship(
        back_populates="language", sa_relationship_kwargs={"lazy": "selectin"}
    )

    translations: List["TranslationSample"] = Relationship(
        back_populates="language", sa_relationship_kwargs={"lazy": "selectin"}
    )

    annotations: List["AnnotationSample"] = Relationship(
        back_populates="language", sa_relationship_kwargs={"lazy": "selectin"}
    )


class UserLanguage(SQLModel, table=True):
    __tablename__ = "user_language"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    user_id: uuid.UUID = Field(foreign_key="user.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")
    proficiency: str = Field(default="beginner")

    total_hours_speech: int = Field(default=0)
    total_sentences_translated: int = Field(default=0)

    # Relationships
    user: "User" = Relationship(
        back_populates="user_languages", sa_relationship_kwargs={"lazy": "selectin"}
    )
    language: "Language" = Relationship(
        back_populates="user_languages", sa_relationship_kwargs={"lazy": "selectin"}
    )
