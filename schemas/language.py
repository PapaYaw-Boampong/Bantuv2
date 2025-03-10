from pydantic import BaseModel, Field
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
    contribution_count: int
    contributor_count: int

    class Config:
        orm_mode = True


class LanguageReadDetailed(LanguageRead):
    contributions: List[Dict[str, Any]] = []
    user_languages: List[Dict[str, Any]] = []


# ===================== USER LANGUAGE SCHEMAS =====================

class UserLanguageBase(BaseModel):
    user_id: str
    language_id: str
    total_hours_speech: Optional[int] = 0
    total_sentences_translated: Optional[int] = 0


class UserLanguageCreate(UserLanguageBase):
    pass


class UserLanguageUpdate(BaseModel):
    total_hours_speech: Optional[int] = None
    total_sentences_translated: Optional[int] = None


class UserLanguageRead(UserLanguageBase):
    id: str

    class Config:
        orm_mode = True
