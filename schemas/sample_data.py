import uuid
from typing import Optional, List, Literal, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, UUID4, field_validator


# ----------- Base Schemas -----------

class SampleBase(BaseModel):
    id: UUID4
    language_id: Optional[uuid.UUID]
    category: Optional[str]
    active: bool
    priority: Optional[int] = 0
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ----------- Transcription -----------

class TranscriptionSampleCreate(BaseModel):
    language_id: UUID4
    transcription_text: str
    category: Optional[str] = None
    active: Optional[bool] = True
    priority: Optional[int] = 0


# ----------- Translation -----------

class TranslationSeedCreate(BaseModel):
    original_text: str
    category: Optional[str] = None
    active: Optional[bool] = True
    priority: Optional[int] = 0


class TranslationSampleCreate(BaseModel):
    language_id: UUID4
    seed_data_id: UUID4


# ----------- Annotation -----------

class AnnotationSeedCreate(BaseModel):
    image_url: str
    annotation_text: str
    category: Optional[str] = None
    active: Optional[bool] = True


class AnnotationSampleCreate(BaseModel):
    language_id: UUID4
    seed_data_id: UUID4
    active: Optional[bool] = True


class BulkTranscriptionSampleUpload(BaseModel):
    """Schema for uploading multiple transcription samples at once"""
    samples: List[TranscriptionSampleCreate] = Field(...)

    @field_validator('samples')
    def check_length(cls, v):
        if not (1 <= len(v)):
            raise ValueError('selected_contribution_ids must have 1 or 2 items')
        return v


class TranslationPairUpload(BaseModel):
    """Schema for uploading translation seed and samples together"""
    seed: TranslationSeedCreate
    translations: List[TranslationSampleCreate] = Field(...)

    @field_validator('translations')
    def check_length(cls, v):
        if not (1 <= len(v)):
            raise ValueError('selected_contribution_ids must have 1 or 2 items')
        return v


class SamplePriorityUpdate(BaseModel):
    """Schema for updating sample priority"""
    priority: int = Field(..., ge=0, le=100, description="Priority level (0-100)")


class SampleLockUpdate(BaseModel):
    """Schema for locking/unlocking samples"""
    sample_ids: List[UUID4] = Field(...)
    state: bool = Field(..., description="Lock state (True=locked, False=unlocked)")

    @field_validator('sample_ids')
    def check_length(cls, v):
        if not (1 <= len(v)):
            raise ValueError('selected_contribution_ids must have 1 or 2 items')
        return v
