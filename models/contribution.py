import uuid
from sqlmodel import SQLModel, Field, Relationship, CheckConstraint
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum
from models.user import User
from models.data_store import TranscriptionSample, TranslationSample
from models.language import Language


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

    upvotes: int = Field(default=0)
    downvotes: int = Field(default=0)

    # Relationships
    user: "User" = Relationship(back_populates="contributions")
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

    # Has the user taken action on this contribution?
    voted: bool = Field(default=False)
    skipped: bool = Field(default=False)

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




# #contributions v3
#
# class TaskType(str, PyEnum):
#     TRANSCRIPTION = "transcription"  # Text → Audio
#     TRANSLATION = "translation"  # English → Target Language
#
#
# class SeedStatus(str, PyEnum):
#     ACTIVE = "active"  # Available for contributions
#     PROCESSING = "processing"  # Enough contributions, being evaluated
#     COMPLETED = "completed"  # Final version(s) selected
#     ARCHIVED = "archived"  # No longer in circulation
#
#
# class SeedData(SQLModel, table=True):
#     """Seed data that users will contribute translations or transcriptions for"""
#     __tablename__ = "seed_data"
#
#     id: uuid.UUID = Field(
#         default_factory=uuid.uuid4,
#         primary_key=True,
#         index=True,
#         nullable=False
#     )
#     task_type: TaskType
#     content: str  # The text to be translated or transcribed
#     status: SeedStatus = Field(default=SeedStatus.ACTIVE)
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow)
#
#     # For translation tasks
#     source_language_id: uuid.UUID = Field(foreign_key="languages.id")
#     target_language_id: Optional[uuid.UUID] = Field(default=None, foreign_key="languages.id")
#
#     # Metadata
#     # difficulty_level: Optional[int] = Field(default=1)  # 1-5 scale
#     category: Optional[str] = None  # e.g., "daily conversation", "technical", "medical"
#
#     # Circulation metrics
#     times_shown: int = Field(default=0)
#     contribution_count: int = Field(default=0)
#
#     # Relationships
#     contributions: List["Contribution"] = Relationship(back_populates="seed_data")
#     source_language: "Language" = Relationship(sa_relationship_kwargs={"foreign_keys": "[SeedData.source_language_id]"})
#     target_language: Optional["Language"] = Relationship(
#         sa_relationship_kwargs={"foreign_keys": "[SeedData.target_language_id]"})
#
#
# class ContributionStatus(str, PyEnum):
#     PENDING = "pending"  # Newly submitted, not yet evaluated
#     UNDER_REVIEW = "under_review"  # Being circulated for voting
#     APPROVED = "approved"  # Accepted as valid
#     REJECTED = "rejected"  # Not accepted
#     FLAGGED = "flagged"  # Potentially problematic
#     FINAL = "final"  # Selected as the final version
#
#
# class Contribution(SQLModel, table=True):
#     __tablename__ = "contributions"
#
#     id: uuid.UUID = Field(
#         default_factory=uuid.uuid4,
#         primary_key=True,
#         index=True,
#         nullable=False
#     )
#     seed_data_id: uuid.UUID = Field(foreign_key="seed_data.id")
#     content: str  # Audio file path or translated text
#     status: ContributionStatus = Field(default=ContributionStatus.PENDING)
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: datetime = Field(default_factory=datetime.utcnow)
#
#     # Metrics
#     upvote_count: int = Field(default=0)
#     downvote_count: int = Field(default=0)
#     flag_count: int = Field(default=0)
#     times_shown: int = Field(default=0)
#
#     # Who contributed this
#     contributor_id: uuid.UUID = Field(foreign_key="users.id")
#
#     # Relationships
#     seed_data: SeedData = Relationship(back_populates="contributions")
#     contributor: "User" = Relationship(back_populates="contributions")
#     votes: List["Vote"] = Relationship(back_populates="contribution")
#
#     # Circulation tracking
#     circulation_records: List["CirculationRecord"] = Relationship(back_populates="contribution")
#
#
# class CirculationRecord(SQLModel, table=True):
#     """Records when a contribution is shown to a user for evaluation"""
#     __tablename__ = "circulation_records"
#
#     id: uuid.UUID = Field(
#         default_factory=uuid.uuid4,
#         primary_key=True,
#         index=True,
#         nullable=False
#     )
#     contribution_id: uuid.UUID = Field(foreign_key="contributions.id")
#     user_id: uuid.UUID = Field(foreign_key="users.id")
#     shown_at: datetime = Field(default_factory=datetime.utcnow)
#
#     # Has the user taken action on this contribution?
#     voted: bool = Field(default=False)
#     skipped: bool = Field(default=False)
#
#     # Relationships
#     contribution: Contribution = Relationship(back_populates="circulation_records")
#     user: "User" = Relationship(back_populates="circulation_records")
