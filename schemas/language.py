from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any


# ===================== LANGUAGE SCHEMAS =====================

class LanguageBase(BaseModel):
    name: str
    description: Optional[str] = None
    code: str  # ISO code


class LanguageCreate(LanguageBase):
    pass


class LanguageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None


class LanguageRead(LanguageBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class LanguageReadDetailed(LanguageRead):
    contribution_count: int
    contributor_count: int
    contributions: List[Dict[str, Any]] = []
    user_languages: List[Dict[str, Any]] = []


# ===================== USER LANGUAGE SCHEMAS =====================

class UserLanguageBase(BaseModel):
    language_id: str
    total_hours_speech: Optional[int] = float
    total_sentences_translated: Optional[int] = 0
    total_annotation_tokens: Optional[int] = 0


class UserLanguageCreate(BaseModel):
    language_id: str
    proficiency: Optional[str] = "Beginner"
    total_hours_speech: Optional[float] = 0
    total_sentences_translated: Optional[int] = 0
    total_annotation_tokens: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class UserLanguageStatsCreate(BaseModel):
    user_language_id: str
    total_hours_speech: Optional[int] = float
    total_sentences_translated: Optional[int] = 0
    total_annotation_tokens: Optional[int] = 0


class UserLanguageUpdate(BaseModel):
    total_hours_speech: Optional[float] = None
    total_sentences_translated: Optional[int] = None
    total_annotation_tokens: Optional[int] = 0


# class UserLanguageRead(UserLanguageBase):
#     id: str
#
#     class Config:
#         orm_mode = True


class LanguageSchema(BaseModel):
    id: str
    name: str
    code: Optional[str] = None  # `code` is optional since you check for it
    description: Optional[str] = None


class UserLanguageRead(BaseModel):
    association_id: str  # UserLanguage ID
    proficiency: str
    language: LanguageSchema  # Nested language details

    model_config = ConfigDict(from_attributes=True)
