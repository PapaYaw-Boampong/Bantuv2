import uuid

from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from user import User
from contribution import Contribution


# ===================== LANGUAGES TABLE =====================
class Language(SQLModel, table=True):
    id: str = Field(
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
    contributions: List["Contribution"] = Relationship(back_populates="language")
    user_languages: List["UserLanguage"] = Relationship(back_populates="language")


class UserLanguage(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id")
    language_id: str = Field(foreign_key="language.id")
    total_hours_speech: Optional[int] = 0
    total_sentences_translated: Optional[int] = 0

    # Relationships
    user: "User" = Relationship(back_populates="user_languages")
    language: "Language" = Relationship(back_populates="user_languages")



