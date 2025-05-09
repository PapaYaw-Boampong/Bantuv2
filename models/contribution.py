import uuid
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict

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
    sample_id: uuid.UUID = Field(foreign_key="annotation_sample.id")

    target_text: str = Field(default="")
    img_url: str = Field(default="")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    flagged: bool = Field(default=False)

    accepted: bool = Field(default=False)

    ancestors: Dict[str, list] = Field(
        sa_column=Column(JSON),
        default_factory=dict
    )

    max_eval_depth: int = Field(default=0)

    # Relationships with optimized loading
    user: "User" = Relationship(
        back_populates="annotation_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    annotation_sample: "AnnotationSample" = Relationship(
        back_populates="annotation_contributions", sa_relationship_kwargs={"lazy": "selectin"}
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
    sample_id: uuid.UUID = Field(foreign_key="transcription_sample.id")

    target_url: str = Field(default="")
    sample_text: str = Field(default="")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    flagged: bool = Field(default=False)
    accepted: bool = Field(default=False)

    ancestors: Dict[str, list] = Field(
        sa_column=Column(JSON),
        default_factory=dict
    )

    max_eval_depth: int = Field(default=0)

    # Relationships with optimized loading
    user: "User" = Relationship(
        back_populates="transcription_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    transcription_sample: "TranscriptionSample" = Relationship(
        back_populates="contributions", sa_relationship_kwargs={"lazy": "selectin"}
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
    sample_id: uuid.UUID = Field(foreign_key="translation_sample.id")

    target_text: str = Field(default="")
    sample_text: str = Field(default="")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    ancestors: Dict[str, list] = Field(
        sa_column=Column(JSON),
        default_factory=dict
    )

    max_eval_depth: int = Field(default=0)

    accepted: bool = Field(default=False)
    flagged: bool = Field(default=False)

    # Relationships with optimized loading
    user: "User" = Relationship(
        back_populates="translation_contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
    translation_sample: "TranslationSample" = Relationship(
        back_populates="contributions", sa_relationship_kwargs={"lazy": "selectin"}
    )
