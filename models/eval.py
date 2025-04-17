import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import SQLModel, Field, Relationship, Column
import datetime
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from models import (
        TranscriptionSample, AnnotationSample, TranslationSample, User, Challenge
    )


class EvaluationInstance(SQLModel, table=True):
    __tablename__ = "evaluation_instance"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    num_branches: int = 3
    challenge_id: uuid.UUID = Field(foreign_key="challenge.id")
    is_complete: bool = False

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

    ab_tests: Optional["ABTest"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )

    evaluation_branches: List["EvaluationBranch"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )

    challenges: Optional["Challenge"] = Relationship(
        back_populates="evaluation_instances",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )


class EvaluationBranch(SQLModel, table=True):
    __tablename__ = "evaluation_branch"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instance_id: uuid.UUID = Field(foreign_key="evaluation_instance.id")
    current_contribution_id: uuid.UUID
    depth: int = 0
    max_depth: int = 5
    is_complete: bool = Field(default=False)

    evaluation_instance: "EvaluationInstance" = Relationship(back_populates="evaluation_branches")
    evaluation_steps: List["EvaluationStep"] = Relationship(
        back_populates="evaluation_branch",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin"
        }
    )


class EvaluationStep(SQLModel, table=True):
    __tablename__ = "evaluation_step"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    branch_id: uuid.UUID = Field(foreign_key="evaluation_branch.id")
    user_id: uuid.UUID = Field(foreign_key="user.id")
    contribution_id: uuid.UUID
    head: bool = Field(default=False)
    assigned_at: datetime = Field(default_factory=None)
    step_number: int = Field(default=1)
    is_complete: bool = Field(default=False)
    is_approved: bool = Field(default=False)

    evaluation_branch: "EvaluationBranch" = Relationship(back_populates="evaluation_steps")
    user: Optional["User"] = Relationship(back_populates="evaluation_steps")


class ABTest(SQLModel, table=True):
    __tablename__ = "ab_test"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instance_id: uuid.UUID = Field(foreign_key="evaluation_instance.id", unique=True)
    is_complete: bool = Field(default=False)

    # New JSON field to hold stages and user-contribution mappings
    ab_test_data: Optional[dict] = Field(
        default_factory=dict,
        sa_column=Column(JSONB)
    )

    evaluation_instance: "EvaluationInstance" = Relationship(back_populates="ab_tests")
