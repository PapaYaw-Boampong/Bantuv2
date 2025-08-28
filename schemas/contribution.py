from pydantic import BaseModel, UUID4, field_validator, Field, ValidationInfo
from typing import Dict, List, Optional
from datetime import datetime


class ContributionCreate(BaseModel):
    """Base schema for creating contributions"""
    id: Optional[str] = None
    target_text: Optional[str] = None
    file_name: Optional[str] = None
    speech_length: Optional[float] = None
    sample_text: Optional[str] = None
    img_url: Optional[str] = None

    @field_validator('target_text', 'file_name', mode='before')
    def validate_target(cls, v, info: ValidationInfo) -> Optional[str]:
        values = info.data
        if not v and not values.get('target_text') and not values.get('file_name'):
            raise ValueError("Either target_text or file_name must be provided")
        return v


class ContributionUpdate(BaseModel):
    """Schema for updating contributions"""
    target_text: Optional[str] = None
    speech_length: Optional[float] = None
    file_name: Optional[str] = None
    active: Optional[bool] = None
    flagged: Optional[bool] = None
    accepted: Optional[bool] = None


class ContributionFilter(BaseModel):
    """Schema for filtering contributions"""
    user_id: Optional[UUID4] = None
    sample_id: Optional[UUID4] = None
    evaluation_instance_id: Optional[UUID4] = None
    active: Optional[bool] = None
    flagged: Optional[bool] = None
    accepted: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class ContributionStats(BaseModel):
    """Schema for contribution statistics"""
    total_contributions: int = 0
    passed_contributions: int = 0
    flagged_contributions: int = 0
    contribution_counts: Dict[str, int] = Field(default_factory=dict)
    user_ranking: Optional[int] = None


class ContributionBase(BaseModel):
    id: UUID4
    user_id: UUID4
    sample_id: UUID4
    created_at: datetime
    accepted: bool
    flagged: bool
    ancestors: Dict[str, List] = {}
    max_eval_depth: int
    

class AnnotationContributionRead(ContributionBase):
    target_text: str
    signed_url: Optional[str] = None  


class TranscriptionContributionRead(ContributionBase):
    sample_text: str
    signed_url: Optional[str] = None  


class TranslationContributionRead(ContributionBase):
    target_text: str
    sample_text: str
    
