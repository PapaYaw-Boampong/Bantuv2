import uuid
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from datetime import datetime
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

    ab_test: Optional["ABTest"] = Relationship(
        back_populates="evaluation_instance",
        sa_relationship_kwargs={
            "uselist": False,
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

    challenge: Optional["Challenge"] = Relationship(
        back_populates="evaluation_instances",
    )


class EvaluationBranch(SQLModel, table=True):
    __tablename__ = "evaluation_branch"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    instance_id: uuid.UUID = Field(foreign_key="evaluation_instance.id")
    current_contribution_id: uuid.UUID
    depth: int = 0
    max_depth: int = 5
    is_complete: bool = Field(default=False)

    evaluation_instance: "EvaluationInstance" = Relationship(
        back_populates="evaluation_branches"
    )
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
    assigned_at: Optional[datetime] = Field(default_factory=None)
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
    final_winner_ids: List[str] = Field(
        sa_column=Column(JSON), default_factory=list
    )
    target_winner_count: int = Field(default=1)  # default = 1, can be >1 for transcription etc.
    stage_count: int = Field(default=0)
    current_stage: int = Field(default=0)  # Track the current active stage
    min_votes_threshold: int = Field(default=3)  # Minimum votes needed for statistical significance
    confidence_level: float = Field(default=0.95)  # Confidence level for statistical significance

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

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
    stage_number: int  # Stage in the tournament
    contribution_a_id: uuid.UUID
    contribution_b_id: uuid.UUID
    is_complete: bool = Field(default=False)
    is_tie: bool = Field(default=False)  # Flag for tracking ties
    winner_id: Optional[uuid.UUID] = Field(default=None)  # Store the winner directly
    vote_count_a: int = Field(default=0)  # Count of votes for contribution A
    vote_count_b: int = Field(default=0)  # Count of votes for contribution B
    min_votes_required: int = Field(default=3)  # Minimum votes needed for this pair

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    ab_test: "ABTest" = Relationship(back_populates="pairs")

    votes: List["ABTestVote"] = Relationship(back_populates="pair")


class ABTestVote(SQLModel, table=True):
    __tablename__ = "ab_test_vote"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pair_id: uuid.UUID = Field(foreign_key="ab_test_pair.id")
    user_id: uuid.UUID
    selected_contribution_id: uuid.UUID
    vote_assigned_at: datetime = Field(default_factory=datetime.utcnow)
    vote_submitted_at: Optional[datetime] = None

    # For randomization tracking
    a_shown_first: bool = Field(default=True)  # Track which option was shown first

    # Weighted score based on user proficiency
    user_proficiency: Optional[int] = None  # Store user proficiency level at time of vote
    weighted_score: Optional[float] = None  # Calculated weighted score

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    pair: "ABTestPair" = Relationship(back_populates="votes")
