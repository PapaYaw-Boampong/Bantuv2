from pydantic import BaseModel, UUID4, field_validator, Field, ValidationInfo
from typing import Dict, List, Optional
from datetime import datetime


class ContributionCreate(BaseModel):
    """Base schema for creating contributions"""
    target_text: Optional[str] = None
    target_url: Optional[str] = None
    speech_length: Optional[float] = None
    sample_text: Optional[str] = None
    sample_id: UUID4
    img_url: Optional[str] = None

    @field_validator('target_text', 'target_url', mode='before')
    def validate_target(cls, v, info: ValidationInfo) -> Optional[str]:
        values = info.data
        if not v and not values.get('target_text') and not values.get('target_url'):
            raise ValueError("Either target_text or target_url must be provided")
        return v


class CustomContributionCreate(BaseModel):
    """Base schema for creating contributions"""
    target_text: Optional[str] = None
    target_url: Optional[str] = None
    speech_length: Optional[float] = None
    language_id: UUID4

    @field_validator('target_text', 'target_url', mode='before')
    def validate_target(cls, v, info: ValidationInfo) -> Optional[str]:
        values = info.data
        if not v and not values.get('target_text') and not values.get('target_url'):
            raise ValueError("Either target_text or target_url must be provided")
        return v


class ContributionUpdate(BaseModel):
    """Schema for updating contributions"""
    target_text: Optional[str] = None
    speech_length: Optional[float] = None
    target_url: Optional[str] = None
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
