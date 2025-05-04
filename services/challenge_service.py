from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select, and_, or_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models.challenge import (
    Challenge, ChallengeParticipation,
    ChallengeStatus, EventType, TaskType, EventCategory
)
from models.user import User
from crud.challenge import ChallengeRuleRepository
from schemas.challenge import (
    ChallengeUpdate, ChallengeParticipationCreate,
    ParticipationUpdate, GetChallenges, ChallengeRulesAdd, UserChallengeFilter
)


def _calculate_progress(challenge: Challenge) -> int:
    """Determine completion percentage based on filled fields"""
    progress = 0

    if challenge.event_type:
        progress += 20
    if challenge.task_type:
        progress += 10
    if challenge.event_category:
        progress += 10
    if challenge.start_date and challenge.end_date:
        progress += 20
    if challenge.challenge_reward_id:
        progress += 20
    if challenge.language_id:
        progress += 20

    return progress  # Cap at 100%


def _get_remaining_fields(challenge: Challenge) -> List[str]:
    """Returns list of fields still needing completion"""
    required = []
    if not challenge.event_type:
        required.append("event_type")
    if not challenge.task_type:
        required.append("task_type")
    if not challenge.event_category:
        required.append("event_category")
    if not challenge.start_date:
        required.append("start_date")
    if not challenge.end_date:
        required.append("end_date")
    if not challenge.language_id:
        required.append("language_id")
    return required


def _get_challenge_status(challenge: Any) -> ChallengeStatus:
    now = datetime.utcnow()
    if challenge.start_date > now:
        return ChallengeStatus.UPCOMING
    elif challenge.end_date < now:
        return ChallengeStatus.COMPLETED
    else:

        return ChallengeStatus.ACTIVE


class ChallengeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_repository = ChallengeRuleRepository(db)

    # Challenge methods
    async def create_challenge(
            self,
            challenge_data: ChallengeUpdate,
            creator: UUID
    ) -> Challenge:

        status = _get_challenge_status(challenge_data)
        challenge = Challenge(
            challenge_name=challenge_data.challenge_name,
            description=challenge_data.description,
            language_id=challenge_data.language_id,
            status=status,
            is_public=True,
            is_published=False,
            creator_id=creator,
            start_date=challenge_data.start_date,
            end_date=challenge_data.end_date,
            task_type=challenge_data.task_type,
            event_category=challenge_data.event_category,
            challenge_reward_id=challenge_data.challenge_reward_id,
            event_type=challenge_data.event_type,
        )
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def add_challenge_rules(
            self, data: ChallengeRulesAdd
    ) -> Challenge:
        challenge = await self.get_challenge(data.challenge_id)
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        if challenge.is_published:
            raise HTTPException(status_code=400, detail="Cannot add new rules to a published challenge")

        await self.rule_repository.add_rules(
            challenge.id,
            data.rules
        )
        return challenge

    async def update_progress(
            self,
            challenge_id: UUID,
            update_data: ChallengeUpdate) -> Optional[Challenge]:
        """Update challenge and recalculate completion %"""
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        # Apply updates
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(challenge, key, value)

        # Recalculate progress
        new_progress = _calculate_progress(challenge)
        challenge.completion_percent = new_progress

        # Update required fields
        # challenge.required_fields = _get_remaining_fields(challenge)

        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def get_challenge(self, challenge_id: UUID) -> Optional[Challenge]:

        result = await self.db.get(Challenge, challenge_id)
        challenge = result if result else None

        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")
        return result

    async def is_published(self, challenge_id: UUID) -> bool:
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return False
        return challenge.is_published

    async def update_challenge(
            self,
            challenge_data: ChallengeUpdate,
            challenge_id: UUID = None,
            creator_id: UUID = None
    ) -> Optional[Challenge]:
        """Create or update a challenge with proper status updates and error handling."""

        update_data = challenge_data.model_dump(exclude_unset=True)

        # Create new challenge if no challenge_id provided
        if not challenge_id:
            challenge = await self.create_challenge(challenge_data, creator_id)

        else:
            challenge = await self.get_challenge(challenge_id)
            if not challenge:
                challenge = await self.create_challenge(challenge_data, creator_id)

            # Update challenge fields
            for key, value in update_data.items():
                if key != 'rules':  # Skip rules separately
                    setattr(challenge, key, value)

        # Update challenge status based on start and end dates
        self._update_challenge_status(challenge, update_data)

        # Recalculate progress and required fields
        challenge.completion_percent = _calculate_progress(challenge)
        # challenge.required_fields = _get_remaining_fields(challenge)

        # Save changes to database
        try:
            await self.db.commit()
            await self.db.refresh(challenge)
            return challenge
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Failed to update challenge: {str(e)}"
            )

    def _update_challenge_status(self, challenge: Challenge, update_data: dict):
        """Helper to update challenge status based on dates."""
        now = datetime.utcnow()
        start_date = update_data.get('start_date', challenge.start_date)
        end_date = update_data.get('end_date', challenge.end_date)

        if start_date and end_date:
            if start_date > now:
                challenge.status = ChallengeStatus.UPCOMING
            elif end_date < now:
                challenge.status = ChallengeStatus.COMPLETED
            else:
                challenge.status = ChallengeStatus.ACTIVE

    async def delete_challenge(self, challenge_id: UUID) -> bool:
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return False
        if challenge.status == ChallengeStatus.COMPLETED or challenge.status == ChallengeStatus.UPCOMING:
            await self.db.delete(challenge)
            await self.db.commit()
            return True
        else:
            raise ValueError("Cannot delete an active challenge")

    async def list_challenges(self, query_params: GetChallenges, creator_id: UUID = None) -> List[Challenge]:
        query = select(Challenge)

        # Apply filters
        if query_params.status:
            query = query.where(Challenge.status == query_params.status)

        if query_params.event_type:
            query = query.where(Challenge.event_type == query_params.event_type)

        if query_params.task_type:
            query = query.where(Challenge.task_type == query_params.task_type)

        if query_params.event_category:
            query = query.where(Challenge.event_category == query_params.event_category)

        if query_params.is_public is not None:
            query = query.where(Challenge.is_public == query_params.is_public)

        if query_params.is_published is not None:
            query = query.where(Challenge.is_published == query_params.is_published)

        if creator_id is not None:
            query = query.where(Challenge.creator_id == creator_id)

        if query_params.language_id is not None:
            query = query.where(Challenge.language_id == query_params.language_id)

        # Apply pagination
        query = query.offset(query_params.skip).limit(query_params.limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def publish_challenge(self, challenge_id: UUID) -> Optional[Challenge]:
        """Mark a challenge as published, making it visible to users"""
        challenge = await self.get_challenge(challenge_id)
        if not challenge or challenge.completion_percent < 100:
            raise ValueError("Cannot publish incomplete challenge")

        challenge.is_published = True

        challenge.status = ChallengeStatus.ACTIVE if (
                challenge.start_date <= datetime.utcnow() <= challenge.end_date
        ) else ChallengeStatus.UPCOMING

        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def unpublish_challenge(self, challenge_id: UUID) -> Optional[Challenge]:
        """Mark a challenge as unpublished, hiding it from users"""
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        if challenge.status == ChallengeStatus.ACTIVE:
            raise ValueError("Cannot unpublish an active challenge")
        challenge.is_published = False
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def update_challenge_status(self, challenge_id: UUID, status: ChallengeStatus) -> Optional[Challenge]:
        """Manually update the status of a challenge"""
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        challenge.status = status
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    # Challenge Participation methods
    async def join_challenge(self,
                             participation_data: ChallengeParticipationCreate
                             ) -> Tuple[ChallengeParticipation, Challenge]:
        """Add a user to a challenge and increment the participant count"""
        # Check if the challenge exists
        challenge = await self.get_challenge(participation_data.event_id)
        if not challenge:
            raise ValueError("Challenge not found")

        # Check if the user is already participating
        result = await self.db.execute(
            select(ChallengeParticipation).where(
                and_(
                    ChallengeParticipation.event_id == participation_data.event_id,
                    ChallengeParticipation.user_id == participation_data.user_id
                )
            )
        )

        result = await self.db.execute(...)
        existing_participation = result.scalar_one_or_none()
        if existing_participation:
            raise ValueError("User is already participating")
        # Create the participation record
        participation = ChallengeParticipation(
            event_id=participation_data.event_id,
            user_id=participation_data.user_id
        )

        # Increment the participant count
        challenge.participant_count += 1

        self.db.add(participation)
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(participation)
        await self.db.refresh(challenge)

        return participation, challenge

    async def leave_challenge(self, event_id: UUID, user_id: UUID) -> bool:
        """Remove a user from a challenge and decrement the participant count"""
        # Find the participation record
        result = await self.db.execute(
            select(ChallengeParticipation).where(
                and_(
                    ChallengeParticipation.event_id == event_id,
                    ChallengeParticipation.user_id == user_id
                )
            )
        )

        participation = result.scalar_one_or_none()
        if not participation:
            return False

        # Get the challenge
        challenge = await self.get_challenge(event_id)
        if not challenge:
            return False

        # Decrement the participant count
        if challenge.participant_count > 0:
            challenge.participant_count -= 1

        # Delete the participation record
        await self.db.delete(participation)
        self.db.add(challenge)
        await self.db.commit()

        return True

    async def get_challenge_participation(
            self,
            event_id: UUID,
            user_id: UUID
    ) -> Optional[ChallengeParticipation]:
        """Get a user's participation record for a specific challenge"""
        result = await self.db.execute(
            select(ChallengeParticipation).where(
                and_(
                    ChallengeParticipation.event_id == event_id,
                    ChallengeParticipation.user_id == user_id
                )
            )
        )
        records = list(result.scalars().all())
        return records[0] if records else None

    async def update_challenge_participation_stats(
            self,
            participation: ChallengeParticipation,
            hours: int = 0,
            sentences: int = 0,
            tokens: int = 0,
            is_contribution: bool = False,
            is_evaluation: bool = False,
            accepted: bool = False,
            points: int = 0
    ) -> ChallengeParticipation:
        participation.total_points += points
        if is_contribution:
            participation.contribution_count += 1
            if accepted:
                participation.accepted_contributions += 1

        if is_evaluation:
            participation.total_hours_speech += hours
            participation.total_sentences_translated += sentences
            participation.total_tokens_produced += tokens

            participation.evaluation_count += 1
            if accepted:
                participation.accepted_evaluations += 1

        # Update scores
        if participation.contribution_count:
            participation.contribution_acceptance_score = (
                    participation.accepted_contributions / participation.contribution_count
            )
        if participation.evaluation_count:
            participation.evaluation_acceptance_score = (
                    participation.accepted_evaluations / participation.evaluation_count
            )

        participation.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(participation)
        return participation

    async def update_participation_stats(
            self,
            event_id: UUID,
            user_id: UUID,
            stats_data: ParticipationUpdate
    ) -> Optional[ChallengeParticipation]:
        participation = await self.get_challenge_participation(event_id, user_id)
        if not participation:
            return None

        return await self.update_challenge_participation_stats(
            participation,
            hours=stats_data.total_hours_speech,
            sentences=stats_data.total_sentences_translated,
            tokens=stats_data.total_tokens_produced,
            is_contribution=stats_data.is_contribution,
            is_evaluation=stats_data.is_evaluation,
            points=stats_data.total_points,
            accepted=stats_data.accepted
        )

    async def get_challenge_participants(self, event_id: UUID, skip: int = 0, limit: int = 100
                                         ) -> List[ChallengeParticipation]:
        """Get all participants for a challenge"""
        query = select(ChallengeParticipation).where(ChallengeParticipation.event_id == event_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_challenges(
            self,
            user_id: UUID,
            filters: UserChallengeFilter
    ) -> List[ChallengeParticipation]:
        """Get all challenges a user is participating in with optional filtering"""

        query = select(ChallengeParticipation).where(
            ChallengeParticipation.user_id == user_id
        )

        if filters.include_challenge_details:
            query = query.options(
                selectinload(ChallengeParticipation.challenge).options(
                    selectinload(Challenge.language),
                    selectinload(Challenge.reward)
                )
            )

        if filters.status:
            query = query.join(Challenge).where(
                Challenge.status == filters.status
            )

        query = query.order_by(
            ChallengeParticipation.updated_at.desc()
        ).offset(filters.skip).limit(filters.limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # Challenge leaderboard methods
    async def get_challenge_leaderboard(
            self, event_id: UUID, skip: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        """Get the leaderboard for a challenge, sorted by total points"""

        # Base query for total count
        count_query = select(func.count()).select_from(
            select(ChallengeParticipation).where(ChallengeParticipation.event_id == event_id).subquery()
        )
        total_count = (await self.db.execute(count_query)).scalar_one()

        # Main query with join
        query = (
            select(ChallengeParticipation, User.username, User.fullname)
            .join(User, ChallengeParticipation.user_id == User.id)
            .where(ChallengeParticipation.event_id == event_id)
            .order_by(desc(ChallengeParticipation.total_points))
            .offset(skip)
            .limit(limit)
        )

        results = await self.db.execute(query)

        leaderboard = []
        for participation, username, fullname in results:
            leaderboard.append({
                "user_id": str(participation.user_id),
                "username": username,
                "name": fullname,
                "points": participation.total_points,
                "hours_speech": participation.total_hours_speech,
                "sentences_translated": participation.total_sentences_translated,
                "tokens_produced": participation.total_tokens_produced,
                "acceptance_rate": participation.acceptance_rate
            })

        return {
            "items": leaderboard,
            "skip": skip,
            "limit": limit,
            "has_next": skip + limit < total_count
        }

    # Challenge status management
    async def update_challenge_statuses(self) -> int:
        """Update the status of all challenges based on current date
        Returns the number of challenges updated"""
        now = datetime.utcnow()

        # Find upcoming challenges that should be active
        upcoming_to_active = select(Challenge).where(
            and_(
                Challenge.status == ChallengeStatus.UPCOMING,
                Challenge.start_date <= now
            )
        )

        upcoming_challenges = await self.db.execute(upcoming_to_active)
        upcoming_challenges = list(upcoming_challenges.scalars().all())

        for challenge in upcoming_challenges:
            if challenge.end_date < now:
                challenge.status = ChallengeStatus.COMPLETED
            else:
                challenge.status = ChallengeStatus.ACTIVE
            self.db.add(challenge)

        # Find active challenges that should be completed
        active_to_completed = select(Challenge).where(
            and_(
                Challenge.status == ChallengeStatus.ACTIVE,
                Challenge.end_date < now
            )
        )

        active_challenges = await self.db.execute(active_to_completed)
        active_challenges = list(active_challenges.scalars().all())

        for challenge in active_challenges:
            challenge.status = ChallengeStatus.COMPLETED
            self.db.add(challenge)

        await self.db.commit()

        return len(upcoming_challenges) + len(active_challenges)
