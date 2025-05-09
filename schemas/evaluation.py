from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, UUID4, field_validator


class EvaluationStepSubmit(BaseModel):
    """Schema for submitting an evaluation step"""
    eval_decision: Optional[bool] = Field(None, description="Accept (True) or reject (False) the contribution")
    correction_id: Optional[UUID4] = Field(None, description="ID of the correction if eval_decision is False")
    run_abtest: bool = Field(False, description="Whether to run A/B test for this step")


class EvaluationInstanceCreate(BaseModel):
    """Schema for creating an evaluation instance"""
    sample_id: UUID4 = Field(..., description="ID of the sample to evaluate")
    contribution_type: str = Field(..., description="Type of contribution (annotation, transcription, translation)")
    num_branches: int = Field(3, description="Number of parallel evaluation branches")


class EvaluationFilter(BaseModel):
    """Schema for filtering evaluations"""
    is_complete: Optional[bool] = None
    challenge_id: Optional[UUID4] = None
    language_id: Optional[UUID4] = None


class ABTestVoteSubmit(BaseModel):
    """Schema for submitting an A/B test vote"""
    selected_contribution_ids: List[UUID4] = Field(...,
                                                  description="IDs of selected contributions (1 or 2 for a tie)")
    contribution_type: str = Field(..., description="Type of contribution")
    challenge_id: Optional[UUID4] = Field(None, description="Optional challenge ID for tracking")
    language_id: Optional[UUID4] = Field(None, description="Language ID for the contributions")

    @field_validator('selected_contribution_ids')
    def check_length(cls, v):
        if not (1 <= len(v) <= 2):
            raise ValueError('selected_contribution_ids must have 1 or 2 items')
        return v
