import uuid
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


# ===================== TRANSCRIPTION CONTRIBUTION TABLE ===============
class TranscriptionContribution(SQLModel, table=True):
    __tablename__ = "transcription_contribution"
    id:  uuid.UUID = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id")
    transcription_sample_id: uuid.UUID = Field(foreign_key="transcription_sample.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = Field(default=False)
    active: bool = Field(default=True)

    frequency: int = Field(default=1)  # Number of times this contribution has been made

    # Relationships
    user: "User" = Relationship(back_populates="transcription_contributions")

    transcription_sample: "TranscriptionSample" = Relationship(back_populates="contributions")

    transcription_circulation_records: list["TranscriptionCirculationRecord"] = Relationship(
        back_populates="transcription_contribution"
    )


# ===================== TRANSLATION CONTRIBUTION TABLE =================
class TranslationContribution(SQLModel, table=True):
    __tablename__ = "translation_contribution"
    id: uuid.UUID = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    translation_sample_id: uuid.UUID = Field(foreign_key="translation_sample.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=True)

    # Relationships
    user: "User" = Relationship(back_populates="translation_contributions")
    translation_sample: "TranslationSample" = Relationship(back_populates="contributions")

    # ✅ Added Relationship for Circulation Records
    translation_circulation_records: list["TranslationCirculationRecord"] = Relationship(
        back_populates="translation_contribution"
    )


# ===================== CIRCULATION RECORDS TABLES =====================
class TranscriptionCirculationRecord(SQLModel, table=True):
    """Records when a transcription contribution is shown to a user for evaluation"""
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

    # Relationships
    transcription_contribution: "TranscriptionContribution" = Relationship(
        back_populates="transcription_circulation_records"
    )
    user: "User" = Relationship(back_populates="transcription_circulation_records")


class TranslationCirculationRecord(SQLModel, table=True):
    """Records when a translation contribution is shown to a user for evaluation"""
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

    # Relationships
    translation_contribution: "TranslationContribution" = Relationship(
        back_populates="translation_circulation_records"
    )
    user: "User" = Relationship(back_populates="translation_circulation_records")
