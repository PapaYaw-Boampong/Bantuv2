import uuid
from typing import Optional, List, Literal, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ----------- Base Schemas -----------

class SampleBase(BaseModel):
    id: uuid.UUID
    language_id: Optional[uuid.UUID]
    category: Optional[str]
    active: bool
    priority: Optional[int] = 0
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ----------- Transcription -----------

class TranscriptionSampleCreate(BaseModel):
    language_id: uuid.UUID
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
    language_id: uuid.UUID
    seed_data_id: uuid.UUID


# ----------- Annotation -----------

class AnnotationSeedCreate(BaseModel):
    image_url: str
    annotation_text: str
    category: Optional[str] = None
    active: Optional[bool] = True


class AnnotationSampleCreate(BaseModel):
    language_id: uuid.UUID
    seed_data_id: uuid.UUID
    active: Optional[bool] = True


