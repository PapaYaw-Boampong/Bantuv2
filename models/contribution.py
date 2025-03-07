import uuid
from sqlmodel import SQLModel, Field, Relationship, CheckConstraint
from typing import Optional, List
from datetime import datetime

from models.user import User
from models.vote import Vote
from models.data_store import TranscriptionSample, TranslationSample


class Contribution(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id")
    transcription_sample_id: Optional[str] = Field(default=None, foreign_key="transcription_sample.id")
    translation_sample_id: Optional[str] = Field(default=None, foreign_key="translation_sample.id")

    transcription_text: Optional[str] = Field(default=None)
    translation_text: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = Field(default=False)
    active: bool = Field(default=True)

    # Relationships
    user: "User" = Relationship(back_populates="contributions")
    votes: List["Vote"] = Relationship(back_populates="contribution")
    transcription_sample: Optional["TranscriptionSample"] = Relationship(back_populates="transcription_contributions")
    translation_sample: Optional["TranslationSample"] = Relationship(back_populates="translation_contributions")

    __table_args__ = (
        CheckConstraint(
            "(transcription_sample_id IS NOT NULL AND translation_sample_id IS NULL) "
            "OR (translation_sample_id IS NOT NULL AND transcription_sample_id IS NULL)",
            name="check_contribution_type"
        ),
    )


class UserContributionAccess(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id", nullable=False)
    contribution_id: str = Field(foreign_key="contribution.id", nullable=False)
    viewed_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: "User" = Relationship(back_populates="user_contribution_access")


#contribution v2
# ===================== TRANSCRIPTION CONTRIBUTION TABLE =====================
# class TranscriptionContribution(SQLModel, table=True):
#     id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
#     user_id: str = Field(foreign_key="user.id")
#     transcription_sample_id: str = Field(foreign_key="transcription_sample.id")
#
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     flagged: bool = Field(default=False)
#     active: bool = Field(default=True)
#
#     # Relationships
#     user: "User" = Relationship(back_populates="transcription_contributions")
#     votes: List["Vote"] = Relationship(back_populates="transcription_contribution")
#     transcription_sample: "TranscriptionSample" = Relationship(back_populates="transcription_contributions")
#
#
# # ===================== TRANSLATION CONTRIBUTION TABLE =====================
# class TranslationContribution(SQLModel, table=True):
#     id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
#     user_id: str = Field(foreign_key="user.id")
#     translation_sample_id: str = Field(foreign_key="translation_sample.id")
#
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     active: bool = Field(default=True)
#
#     # Relationships
#     user: "User" = Relationship(back_populates="translation_contributions")
#     votes: List["Vote"] = Relationship(back_populates="translation_contribution")
#     translation_sample: "TranslationSample" = Relationship(back_populates="translation_contributions")


#
# #contribution v3
# class Contribution(SQLModel, table=True):
#     id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
#     user_id: str = Field(foreign_key="user.id")
#
#     data_id: str  # Can reference either TranscriptionSample or TranslationSample
#     data_type: str  # "transcription" or "translation" (indicates what data_id points to)
#
#     content: str  # Either text (for transcriptions/translations) or a URL (for speech audio)
#     content_type: str  # "text" or "audio_url"
#
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     flagged: bool = Field(default=False)
#     active: bool = Field(default=True)
#
#     # Relationships
#     user: "User" = Relationship(back_populates="contributions")
#     votes: List["Vote"] = Relationship(back_populates="contribution")
#
