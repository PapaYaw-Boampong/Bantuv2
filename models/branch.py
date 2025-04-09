import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models import (
        TranscriptionSample, AnnotationSample, TranslationSample
    )


class EvaluationInstance(SQLModel, table=True):
    __tablename__ = "evaluation_instance"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    num_branches: int = 3
    max_depth: int = 5
    is_complete: bool = False

    branches: List["EvaluationBranch"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )

    transcription_sample: Optional["TranscriptionSample"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    translation_sample: Optional["TranslationSample"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    annotation_sample: Optional["AnnotationSample"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={"lazy": "selectin"}
    )


class EvaluationBranch(SQLModel, table=True):
    __tablename__ = "evaluation_branch"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instance_id: uuid.UUID = Field(foreign_key="evaluationinstance.id")
    current_contribution_id: uuid.UUID
    depth: int = Field(default=0)
    complete: bool = Field(default=False)

    evaluation_instance: "EvaluationInstance" = Relationship(back_populates="branches")
