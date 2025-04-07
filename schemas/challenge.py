from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, UUID4, ConfigDict
from models.challenge import EventType, TaskType, EventCategory, ChallengeStatus


# Pydantic models for request/response
class ChallengeCreate(BaseModel):
    challenge_name: str
    description: Optional[str] = None
    event_type: EventType
    task_type: TaskType
    event_category: EventCategory
    start_date: datetime
    end_date: datetime
    is_public: bool = True
    reward: UUID4  # Reference to the reward ID
    target_contribution_count: Optional[int] = None


class ChallengeUpdate(BaseModel):
    challenge_name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    task_type: Optional[TaskType] = None
    event_category: Optional[EventCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[ChallengeStatus] = None
    is_public: Optional[bool] = None
    is_published: Optional[bool] = None
    reward: Optional[UUID4] = None
    target_contribution_count: Optional[int] = None


class ChallengeParticipationCreate(BaseModel):
    event_id: UUID4
    user_id: UUID4


class ChallengeParticipationUpdate(BaseModel):
    total_hours_speech: Optional[int] = None
    total_sentences_translated: Optional[int] = None
    total_tokens_produced: Optional[int] = None
    total_points: Optional[int] = None
    acceptance_rate: Optional[float] = None


class UserStatsUpdate(BaseModel):
    total_hours_speech: Optional[int] = None
    total_sentences_translated: Optional[int] = None
    total_tokens_produced: Optional[int] = None
    total_points: Optional[int] = None
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
    challenge_name: str
    description: Optional[str] = None
    event_type: EventType
    task_type: TaskType
    event_category: EventCategory
    start_date: datetime
    end_date: datetime
    status: ChallengeStatus
    is_public: bool
    is_published: bool
    participant_count: int
    contribution_count: int

    model_config = ConfigDict(from_attributes=True)


class ChallengeDetailResponse(ChallengeSummary):
    reward: str  # UUID of the reward
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GetChallenges(BaseModel):
    status: Optional[ChallengeStatus] = None
    event_type: Optional[EventType] = None
    task_type: Optional[TaskType] = None
    event_category: Optional[EventCategory] = None
    is_public: Optional[bool] = None
    is_published: Optional[bool] = None
    skip: int = 0
    limit: int = 100
