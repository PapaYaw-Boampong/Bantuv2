import uuid
from typing import Optional, List, Literal, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, UUID4, field_validator


# ----------- Base Schemas -----------

class SampleBase(BaseModel):
    id: UUID4
    language_id: Optional[uuid.UUID]
    active: bool
    priority: Optional[int] = 0
    created_at: Optional[datetime]
    evaluation_instance_id: Optional[str];
    model_config = ConfigDict(from_attributes=True)


# ----------- Seed Data Output Schemas -----------
class TranslationSeedDataOut(BaseModel):
    id: UUID4
    original_text: str
    category: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class AnnotationSeedDataOut(BaseModel):
    id: UUID4
    file_name: str
    annotation_text: str
    category: Optional[str]
    signed_url: Optional[str] = None  # ← Already correct

    model_config = ConfigDict(from_attributes=True)


# ----------- Sample Output Schemas -----------

class TranscriptionSampleOut(SampleBase):
    category: Optional[str]
    transcription_text: str


class TranslationSampleOut(SampleBase):
    seed_data_id: uuid.UUID
    translation_seed_data: Optional[TranslationSeedDataOut]


class AnnotationSampleOut(SampleBase):
    seed_data_id: uuid.UUID
    annotation_seed_data: Optional[AnnotationSeedDataOut] = None

    model_config = ConfigDict(from_attributes=True)


# ----------- Sample List Output Schemas -----------

class TranslationSampleListResponse(BaseModel):
    samples: List[TranslationSampleOut]
    count: int


class TranscriptionSampleListResponse(BaseModel):
    samples: List[TranscriptionSampleOut]
    count: int


class AnnotationSampleListResponse(BaseModel):
    samples: List[AnnotationSampleOut]
    count: int


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
    file_name: str
    hint: str
    source: str
    category: Optional[str] = None
    active: Optional[bool] = True
    id: uuid.UUID 


class AnnotationSampleCreate(BaseModel):
    language_id: UUID4
    seed_data_id: UUID4
    eval: Optional[bool] = True


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
