import uuid
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON
from sqlalchemy import Column
from typing import List, Dict
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Language, TranscriptionContribution, TranslationContribution, AnnotationContribution \
        , EvaluationInstance


# ===================== TRANSCRIPTION SAMPLE TABLE =====================
class TranscriptionSample(SQLModel, table=True):
    """
        Represents a sample of transcribed speech.

        This model stores information about a single transcription sample, including the
        audio URLs, transcription text, category, and creation date. It also establishes
        relationships with the Language and TranscriptionContribution models.Transcription
        samples start of with the native language.
        """
    __tablename__ = "transcription_sample"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    language_id: uuid.UUID = Field(foreign_key="language.id")

    evaluation_instance_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="evaluation_instance.id"
    )

    # Stores multiple validated speech samples of the audio
    audio_urls: List[Dict[str, str]] = Field(
        sa_column=Column(JSON),
        default=[]
    )

    transcription_text: str  # Stores the transcribed text
    category: str = Field(default=None, nullable=True)  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when assigned to a user
    eval: bool = Field(default=False)  # Becomes True when assigned to an evaluation instance
    store: int = Field(default=0)  # Store for the sample, used for tracking

    priority: int = Field(default=0)  # Priority for transcription, higher means more important

    # Relationships
    language: "Language" = Relationship(
        back_populates="transcriptions",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    contributions: List["TranscriptionContribution"] = Relationship(
        back_populates="transcription_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    evaluation_instance: Optional["EvaluationInstance"] = Relationship(
        back_populates="transcription_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin",
                                "single_parent": True}
    )


# ===================== TRANSLATION SEED DATA TABLE =====================
class TranslationSeedData(SQLModel, table=True):
    """
       Represents the original base text (e.g., English) before translations are made in various languages.

       This model stores information about the original text, including the text itself,
       category, and creation date. It also establishes relationships with the TranslationSample model.
       """
    __tablename__ = "translation_seed_data"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    original_text: str  # The base text (usually English or a major language)
    category: str = Field(default=None, nullable=True)  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when assigned to a user

    priority: int = Field(default=0)  # Priority for translation, higher means more important
    # Relationships
    translations: List["TranslationSample"] = Relationship(
        back_populates="translation_seed_data",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== TRANSLATION SAMPLE TABLE =====================
class TranslationSample(SQLModel, table=True):
    """
        Represents a sample of translated text.

        This model stores information about a single translation sample, including the
        translated text, seed data ID, language ID, and creation date. It also establishes
        relationships with the TranslationSeedData and Language models.
        """
    __tablename__ = "translation_sample"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True

    )

    seed_data_id: uuid.UUID = Field(foreign_key="translation_seed_data.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")
    evaluation_instance_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="evaluation_instance.id"
    )

    translated_text: str  # Final translated version of the original text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when assigned to a user
    eval: bool = Field(default=False)  # Becomes True when assigned to an evaluation instance

    priority: int = Field(default=0)  # Priority for translation, higher means more important

    # stores records for frequency of words in the translation and contribution frequencies
    words: Dict[str, int] = Field(sa_column=Column(JSON), default_factory=dict)

    store: int = Field(default=0)

    # Relationships
    translation_seed_data: "TranslationSeedData" = Relationship(
        back_populates="translations",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    language: "Language" = Relationship(
        back_populates="translations",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    contributions: List["TranslationContribution"] = Relationship(
        back_populates="translation_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    evaluation_instance: Optional["EvaluationInstance"] = Relationship(
        back_populates="translation_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin",
                                "single_parent": True}
    )


# ===================== ANNOTATION SAMPLE TABLE =====================
class AnnotationSeedData(SQLModel, table=True):
    """
        Represents the seed data for annotations.

        This model stores information about the annotation seed data, including the
        image URL, annotation text, category, and creation date. It also establishes
        relationships with the AnnotationSample model. The data stored here is the base
        seed data for the annotations, in English or a major language.
        """
    __tablename__ = "annotation_seed_data"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    image_url: str = Field(default=None, nullable=False)
    annotation_text: str = Field(default=None, nullable=False)
    category: str = Field(default=None, nullable=True)  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)

    priority: int = Field(default=0)  # Priority for annotation, higher means more important

    # Relationships
    annotations: List["AnnotationSample"] = Relationship(
        back_populates="annotation_seed_data",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== ANNOTATION SAMPLE TABLE =====================


class AnnotationSample(SQLModel, table=True):
    """
        Represents a sample of annotated data.

        This model stores information about a single annotation sample, including the
        annotation result, seed data ID, language ID, and creation date. It also establishes
        relationships with the AnnotationSeedData and Language models.
        """
    __tablename__ = "annotation_sample"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    seed_data_id: uuid.UUID = Field(foreign_key="annotation_seed_data.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")
    evaluation_instance_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="evaluation_instance.id"
    )
    annotation_result: List[Dict[str, str]] = Field(
        sa_column=Column(JSON),
        default=[]
    )
    words: Dict[str, int] = Field(sa_column=Column(JSON), default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)
    eval: bool = Field(default=False)  # Becomes True when assigned to an evaluation instance

    priority: int = Field(default=0)  # Priority for annotation, higher means more important

    store: int = Field(default=0)

    # Relationships
    annotation_seed_data: "AnnotationSeedData" = Relationship(
        back_populates="annotations",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    language: "Language" = Relationship(
        back_populates="annotations",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    annotation_contributions: List["AnnotationContribution"] = Relationship(
        back_populates="annotation_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )
    evaluation_instance: Optional["EvaluationInstance"] = Relationship(
        back_populates="annotation_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin",
                                "single_parent": True}
    )
