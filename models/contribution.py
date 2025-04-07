import uuid
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from models import User, TranscriptionSample, TranslationSample, AnnotationSample


# ===================== ANNOTATION CONTRIBUTION TABLE ===============
class AnnotationContribution(SQLModel, table=True):
    __tablename__ = "annotation_contribution"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id")
    annotation_sample_id: uuid.UUID = Field(foreign_key="annotation_sample.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = Field(default=False)
    active: bool = Field(default=True)

    # Relationships with optimized loading
    user: "User" = Relationship(
        back_populates="annotation_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    annotation_sample: "AnnotationSample" = Relationship(
        back_populates="annotation_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    annotation_circulation_records: List["AnnotationCirculationRecord"] = Relationship(
        back_populates="annotation_contribution",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== TRANSCRIPTION CONTRIBUTION TABLE ===============
class TranscriptionContribution(SQLModel, table=True):
    __tablename__ = "transcription_contribution"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id")
    transcription_sample_id: uuid.UUID = Field(foreign_key="transcription_sample.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = Field(default=False)
    active: bool = Field(default=True)

    frequency: int = Field(default=1)  # Number of times this contribution has been made

    # Relationships with optimized loading
    user: "User" = Relationship(
        back_populates="transcription_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    transcription_sample: "TranscriptionSample" = Relationship(
        back_populates="contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    transcription_circulation_records: List["TranscriptionCirculationRecord"] = Relationship(
        back_populates="transcription_contribution", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== TRANSLATION CONTRIBUTION TABLE =================
class TranslationContribution(SQLModel, table=True):
    __tablename__ = "translation_contribution"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    user_id: uuid.UUID = Field(foreign_key="user.id")
    translation_sample_id: uuid.UUID = Field(foreign_key="translation_sample.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=True)

    # Relationships with optimized loading
    user: "User" = Relationship(
        back_populates="translation_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    translation_sample: "TranslationSample" = Relationship(
        back_populates="contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    translation_circulation_records: List["TranslationCirculationRecord"] = Relationship(
        back_populates="translation_contribution", sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== CIRCULATION RECORDS TABLES =====================
class TranscriptionCirculationRecord(SQLModel, table=True):
    __tablename__ = "transcription_circulation_record"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    transcription_contribution_id: uuid.UUID = Field(foreign_key="transcription_contribution.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    shown_at: datetime = Field(default_factory=datetime.utcnow)

    # Has the user taken action on this contribution?
    voted: bool = Field(default=False)
    skipped: bool = Field(default=False)

    # Relationships with optimized loading
    transcription_contribution: "TranscriptionContribution" = Relationship(
        back_populates="transcription_circulation_records", sa_relationship_kwargs={"lazy": "selectin"}
    )
    user: "User" = Relationship(
        back_populates="transcription_circulation_records", sa_relationship_kwargs={"lazy": "selectin"}
    )


class TranslationCirculationRecord(SQLModel, table=True):
    """Records when a translation contribution is shown to a user for evaluation"""
    __tablename__ = "translation_circulation_record"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    translation_contribution_id: uuid.UUID = Field(foreign_key="translation_contribution.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    shown_at: datetime = Field(default_factory=datetime.utcnow)

    # Has the user taken action on this contribution?
    voted: bool = Field(default=False)
    skipped: bool = Field(default=False)

    # Relationships with optimized loading
    translation_contribution: "TranslationContribution" = Relationship(
        back_populates="translation_circulation_records", sa_relationship_kwargs={"lazy": "selectin"}
    )
    user: "User" = Relationship(
        back_populates="translation_circulation_records", sa_relationship_kwargs={"lazy": "selectin"}
    )


class AnnotationCirculationRecord(SQLModel, table=True):
    __tablename__ = "annotation_circulation_record"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    annotation_contribution_id: uuid.UUID = Field(foreign_key="annotation_contribution.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    shown_at: datetime = Field(default_factory=datetime.utcnow)
    voted: bool = Field(default=False)
    skipped: bool = Field(default=False)

    # Relationships with optimized loading
    annotation_contribution: "AnnotationContribution" = Relationship(
        back_populates="annotation_circulation_records", sa_relationship_kwargs={"lazy": "selectin"}
    )
    user: "User" = Relationship(
        back_populates="annotation_circulation_records", sa_relationship_kwargs={"lazy": "selectin"}
    )
