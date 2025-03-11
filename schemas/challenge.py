from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from models.challenge import EventType


# Pydantic models for request/response
class ChallengeCreate(BaseModel):
    challenge_name: str
    description: Optional[str] = None
    EventType: EventType
    start_date: datetime
    end_date: datetime
    target_contribution_count: Optional[int] = None


class ChallengeUpdate(BaseModel):
    challenge_name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    target_contribution_count: Optional[int] = None


class UserStatsUpdate(BaseModel):
    total_hours_speech: Optional[int] = None
    total_sentences_translated: Optional[int] = None
    total_tokens_produced: Optional[int] = None
    acceptance_rate: Optional[float] = None


class ChallengeParticipantResponse(BaseModel):
    user_id: str
    username: str
    name: str
    points: int
    hours_speech: int
    sentences_translated: int
    tokens_produced: int
    acceptance_rate: float


class ChallengeSummary(BaseModel):
    id: str
    name: str
    type: EventType
    start_date: datetime
    end_date: datetime
    is_active: bool
    participant_count: int
    contribution_count: int
