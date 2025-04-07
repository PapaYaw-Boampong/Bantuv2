import uuid
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON
from sqlalchemy import Column
from typing import List, Dict
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Language, TranscriptionContribution, TranslationContribution, AnnotationContribution


# ===================== TRANSCRIPTION SAMPLE TABLE =====================
class TranscriptionSample(SQLModel, table=True):
    """
        Represents a sample of transcribed speech.

        This model stores information about a single transcription sample, including the
        audio URLs, transcription text, category, and creation date. It also establishes
        relationships with the Language and TranscriptionContribution models.Transcription
        samples start of with the native language.

        Attributes:
            id (uuid.UUID): Unique identifier for the transcription sample.
            language_id (uuid.UUID): Foreign key referencing the Language model.
            audio_urls (List[Dict[str, str]]): List of audio URLs associated with the transcription sample.
            transcription_text (str): The transcribed text of the audio sample.
            category (str): Category of the transcription sample (e.g., "daily conversation", "technical", "medical").
            created_at (datetime): Date and time when the transcription sample was created.
            active (bool): Whether the transcription sample is active or not.
            sm1 (int): Stores branch 1 step.
            sm2 (int): Stores branch 2 step.
            sm3 (int): Stores branch 3 step.
        """
    __tablename__ = "transcription_sample"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    language_id: uuid.UUID = Field(foreign_key="language.id")

    # Stores multiple validated speech samples of the audio

    audio_urls: List[Dict[str, str]] = Field(
        sa_column=Column(JSON),
        default=[]
    )

    transcription_text: str  # Stores the transcribed text
    category: str = Field(default=None, nullable=True)  # e.g., "daily conversation", "technical", "medical"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when it meets a threshold of upvotes

    sm1: int = Field(default=0)  # Stores branch 1 step
    sm2: int = Field(default=0)  # Stores branch 2 step
    sm3: int = Field(default=0)  # Stores branch 3 step

    # Relationships
    language: "Language" = Relationship(
        back_populates="transcriptions",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    contributions: List["TranscriptionContribution"] = Relationship(
        back_populates="transcription_sample",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== TRANSLATION SEED DATA TABLE =====================
class TranslationSeedData(SQLModel, table=True):
    """
       Represents the original base text (e.g., English) before translations are made in various languages.

       This model stores information about the original text, including the text itself,
       category, and creation date. It also establishes relationships with the TranslationSample model.

       Attributes:
           id (uuid.UUID): Unique identifier for the translation seed data.
           original_text (str): The original base text.
           category (str): Category of the translation seed data (e.g., "daily conversation", "technical", "medical").
           created_at (datetime): Date and time when the translation seed data was created.
           active (bool): Whether the translation seed data is active or not.
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
    active: bool = Field(default=False)  # Becomes True when a threshold of upvotes is met

    # # Relationships
    # translations: List["TranslationSample"] = Relationship(back_populates="translation_seed_data")

    # Relationships
    translations: List["TranslationSample"] = Relationship(
        back_populates="translation_seed_data",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "lazy": "selectin"}
    )


# ===================== TRANSLATION SAMPLE TABLE =====================
class TranslationSample(SQLModel, table=True):
    """
        Represents a validated translation of a seed across multiple languages.

        This model stores information about a single translation sample, including the
        translated text, seed data ID, language ID, and creation date. It also establishes
        relationships with the TranslationSeedData, Language, and TranslationContribution models.


        Attributes:
            id (uuid.UUID): Unique identifier for the translation sample.
            seed_data_id (uuid.UUID): Foreign key referencing the TranslationSeedData model.
            language_id (uuid.UUID): Foreign key referencing the Language model.
            translated_text (str): The translated text of the original seed.
            created_at (datetime): Date and time when the translation sample was created.
            active (bool): Whether the translation sample is active or not.
            sm1 (int): Stores branch 1 step.
            sm2 (int): Stores branch 2 step.
            sm3 (int): Stores branch 3 step.
        """
    __tablename__ = "translation_sample"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True

    )

    seed_data_id: uuid.UUID = Field(foreign_key="translation_seed_data.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")

    translated_text: str  # The translated version of the original text
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)  # Becomes True when a threshold of upvotes is met

    sm1: int = Field(default=0)  # Stores branch 1 step
    sm2: int = Field(default=0)  # Stores branch 2 step
    sm3: int = Field(default=0)  # Stores branch 3 step

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


# ===================== ANNOTATION SAMPLE TABLE =====================
class AnnotationSeedData(SQLModel, table=True):
    """
        Represents the seed data for annotations.

        This model stores information about the annotation seed data, including the
        image URL, annotation text, category, and creation date. It also establishes
        relationships with the AnnotationSample model. The data stored here is the base
        seed data for the annotations, in English or a major language.

        Attributes:
            id (uuid.UUID): Unique identifier for the annotation seed data.
            image_url (str): URL of the image associated with the annotation seed data.
            annotation_text (str): The annotation text.
            category (str): Category of the annotation seed data (e.g., "daily conversation", "technical", "medical").
            created_at (datetime): Date and time when the annotation seed data was created.
            active (bool): Whether the annotation seed data is active or not.
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

        Attributes:
            id (uuid.UUID): Unique identifier for the annotation sample.
            seed_data_id (uuid.UUID): Foreign key referencing the AnnotationSeedData model.
            language_id (uuid.UUID): Foreign key referencing the Language model.
            annotation_result (List[Dict[str, str]]): The annotation result.
            created_at (datetime): Date and time when the annotation sample was created.
            active (bool): Whether the annotation sample is active or not.
        """
    __tablename__ = "annotation_sample"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    seed_data_id: uuid.UUID = Field(foreign_key="annotation_seed_data.id")
    language_id: uuid.UUID = Field(foreign_key="language.id")
    annotation_result: List[Dict[str, str]] = Field(
        sa_column=Column(JSON),
        default=[]
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=False)

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

