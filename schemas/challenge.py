from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, UUID4, ConfigDict, field_validator
from models.challenge import EventType, TaskType, EventCategory, ChallengeStatus
from schemas.rewards import ChallengeRewardUpdate, ChallengeReward


# Pydantic models for request/response


class ChallengeRule(BaseModel):
    id: Optional[UUID4] = None
    rule_title: str
    rule_description: str
    is_required: bool
    model_config = ConfigDict(from_attributes=True)


class ChallengeRulesAdd(BaseModel):
    challenge_id: UUID4
    rules: List[ChallengeRule]


class ChallengeCreate(BaseModel):
    challenge_name: str
    description: Optional[str] = None


class Challenge(ChallengeCreate):
    id: UUID4
    creator_id: UUID4
    event_type: EventType
    task_type: TaskType
    event_category: EventCategory
    start_date: datetime
    end_date: datetime
    status: ChallengeStatus
    language_id: UUID4
    is_public: bool = True
    is_published: bool = False
    challenge_reward_id: Optional[UUID4] = None  # Reference to the reward ID
    participation_count: Optional[int] = 0
    completion_percent: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


class ChallengeUpdate(BaseModel):
    id: Optional[UUID4] = None
    challenge_name: Optional[str] = None
    language_id: Optional[UUID4] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    task_type: Optional[TaskType] = None
    event_category: Optional[EventCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[ChallengeStatus] = None
    is_public: Optional[bool] = None
    is_published: Optional[bool] = None
    creator_id: Optional[UUID4] = None
    challenge_reward_id: Optional[UUID4] = None  # Reference to the reward ID
    challenge_status: Optional[ChallengeStatus] = None
    target_contribution_count: Optional[int] = None


class SaveChallengeData(BaseModel):
    challenge_data: Optional[ChallengeUpdate] = None
    challenge_rules: Optional[List[ChallengeRule]] = None
    challenge_reward: Optional[ChallengeRewardUpdate] = None


class SaveChallengeResponse(BaseModel):
    challenge: Challenge
    reward: Optional[ChallengeReward] = None
    rules: Optional[List[ChallengeRule]] = None


class ChallengeParticipationCreate(BaseModel):
    event_id: UUID4
    user_id: UUID4


class ParticipationUpdate(BaseModel):
    total_hours_speech: Optional[int] = 0
    total_sentences_translated: Optional[int] = 0
    total_tokens_produced: Optional[int] = 0
    total_points: Optional[int] = 0

    is_evaluation: Optional[bool] = False
    is_contribution: Optional[bool] = False

    accepted: Optional[bool] = False


# class UserStatsUpdate(BaseModel):
#     total_hours_speech: Optional[int] = None
#     total_sentences_translated: Optional[int] = None
#     total_tokens_produced: Optional[int] = None
#     total_points: Optional[int] = None
#     acceptance_rate: Optional[float] = None


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
    creator: str
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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserChallengeFilter(BaseModel):
    creator_id: Optional[UUID4] = None
    skip: int = 0
    limit: int = 100
    status: Optional[ChallengeStatus] = None
    include_challenge_details: bool = True


class ChallengeDetailResponse(ChallengeSummary):
    reward: str  # UUID of the reward
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GetChallenges(BaseModel):
    creator_id: Optional[UUID4] = None
    language_id: Optional[UUID4] = None
    status: Optional[ChallengeStatus] = None
    event_type: Optional[EventType] = None
    task_type: Optional[TaskType] = None
    event_category: Optional[EventCategory] = None
    is_public: Optional[bool] = None
    is_published: Optional[bool] = None
    skip: Optional[int] = 0  # int = 0
    limit: Optional[int] = 100  # int = 100


class AddChallengeReward(BaseModel):
    challenge_id: UUID4
    reward_id: UUID4


class UserChallengeStatsOut(BaseModel):
    user_id: UUID4
    event_id: UUID4
    rank: Optional[int]
    total_points: int
    contribution_count: int
    accepted_contributions: int
    evaluation_count: int
    accepted_evaluations: int
    contribution_acceptance_score: Optional[float]
    evaluation_acceptance_score: Optional[float]
    total_hours_speech: Optional[int] = None
    total_sentences_translated: Optional[int] = None
    total_tokens_produced: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ChallengeStatsOut(BaseModel):
    event_id: UUID4
    participant_count: int
    contribution_count: int
    evaluation_count: int
    avg_contribution_acceptance: float
    avg_evaluation_acceptance: float
    total_hours_speech: Optional[int] = None
    total_sentences_translated: Optional[int] = None
    total_tokens_produced: Optional[int] = None
    completion_percent: Optional[float] = None
