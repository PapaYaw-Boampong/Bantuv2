import uuid
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, DateTime
from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from models import (
        TranscriptionSample, AnnotationSample, TranslationSample, User, Challenge
    )


class EvaluationInstance(SQLModel, table=True):
    __tablename__ = "evaluation_instance"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    num_branches: int = Field(default=2)
    challenge_id: uuid.UUID = Field(foreign_key="challenge.id", nullable=True)
    is_complete: bool = False

    ancestors: List[str] = Field(
        sa_column=Column(JSON),
        default_factory=dict
    )


    transcription_sample: Optional["TranscriptionSample"] = Relationship(
        back_populates="evaluation_instance",
    )
    translation_sample: Optional["TranslationSample"] = Relationship(
        back_populates="evaluation_instance",
    )
    annotation_sample: Optional["AnnotationSample"] = Relationship(
        back_populates="evaluation_instance",
    )

    ab_test: Optional["ABTest"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={
            "uselist": False,
            "cascade": "all, delete",
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

    challenge: Optional["Challenge"] = Relationship(
        back_populates="evaluation_instances",
    )


class EvaluationBranch(SQLModel, table=True):
    __tablename__ = "evaluation_branch"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instance_id: uuid.UUID = Field(foreign_key="evaluation_instance.id")
    current_contribution_id: uuid.UUID
    depth: int = 1
    max_depth: int = 5
    is_complete: bool = Field(default=False)

    evaluation_instance: "EvaluationInstance" = Relationship(
        back_populates="evaluation_branches",
         sa_relationship_kwargs={
            "lazy": "selectin"
        }
    )
    evaluation_steps: List["EvaluationStep"] = Relationship(
        back_populates="evaluation_branch",
        sa_relationship_kwargs={
            "cascade": "all, delete",
            "lazy": "selectin"
        }
    )


class EvaluationStep(SQLModel, table=True):
    __tablename__ = "evaluation_step"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    branch_id: uuid.UUID = Field(foreign_key="evaluation_branch.id")
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=True)
    b_contribution_id: uuid.UUID
    head: bool = Field(default=False)

    assigned_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    step_number: int = Field(default=1)

    is_complete: bool = Field(default=False)

    abtest_decision: Optional[str] = Field(default=None)

    evaluation_decision: Optional[bool] = Field(default=None)

    run_ab_test: bool = Field(default=False)  # Flag to indicate if AB test should be run

    a_contribution_id: Optional[uuid.UUID] = Field(default=None, nullable=True)  # Alternative contribution from previous step

    next_alt_contribution_id: Optional[uuid.UUID] = Field(default=None, nullable=True)  # Next alternative contribution ID

    evaluation_branch: "EvaluationBranch" = Relationship(back_populates="evaluation_steps")

    user: Optional["User"] = Relationship(back_populates="evaluation_steps")


class ABTest(SQLModel, table=True):
    __tablename__ = "ab_test"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instance_id: uuid.UUID = Field(foreign_key="evaluation_instance.id", unique=True)

    is_complete: bool = Field(default=False)
    final_winner_ids: List[str] = Field(
        sa_column=Column(JSON), default_factory=list
    )

    target_winner_count: int = Field(default=1)  # default = 1, can be >1 for transcription etc.
    test_depth: int = Field(default=0)
    current_stage: int = Field(default=0)  # Track the current active stage

    created_at: datetime =  Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    # Enhanced data structure for storing test metadata
    ab_test_data: Optional[dict] = Field(default=None, sa_column=Column(JSONB))  # Using JSONB for better querying

    evaluation_instance: Optional["EvaluationInstance"] = Relationship(
        back_populates="ab_test",
        sa_relationship_kwargs={"uselist": False, "lazy": "selectin"},
    )

    pairs: List["ABTestPair"] = Relationship(back_populates="ab_test")


class ABTestPair(SQLModel, table=True):
    __tablename__ = "ab_test_pair"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    ab_test_id: uuid.UUID = Field(foreign_key="ab_test.id")
    stage_number: int  = Field (default=0)

    contribution_a_id: uuid.UUID = Field (default_factory=uuid.uuid4)
    contribution_b_id: uuid.UUID = Field (default_factory=uuid.uuid4)
    is_complete: bool = Field(default=False)
    is_tie: bool = Field(default=False)  # Flag for tracking ties

    winner_ids: Optional[List[uuid.UUID]] = Field(
        sa_column=Column(JSON),
        default_factory=list
    )  # Store the winner directly

    created_at: datetime =  Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime =  Field(
        default = None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    ab_test: "ABTest" = Relationship(back_populates="pairs")

    votes: List["ABTestVote"] = Relationship(back_populates="pair")


class ABTestVote(SQLModel, table=True):
    __tablename__ = "ab_test_vote"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pair_id: uuid.UUID = Field(foreign_key="ab_test_pair.id")
    user_id: uuid.UUID = Field (default_factory=uuid.uuid4)
    selected_contribution_ids: List[uuid.UUID] = Field(sa_column=Column(JSON))  #Store selected contribution IDs

    vote_assigned_at: datetime =  Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    vote_submitted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )


    # For randomization tracking
    a_shown_first: bool = Field(default=True)  # Track which option was shown first

    created_at: datetime =  Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    updated_at: datetime =  Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    pair: "ABTestPair" = Relationship(back_populates="votes")
