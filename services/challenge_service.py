from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid
from sqlmodel import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from models.challenge import (
    Challenge, ChallengeParticipation,
    ChallengeStatus, EventType, TaskType, EventCategory
)
from models.user import User, UserStatistics
from schemas.challenge import (
    ChallengeCreate, ChallengeUpdate, ChallengeParticipationCreate,
    ChallengeParticipationUpdate, GetChallenges
)



class ChallengeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Challenge methods
    async def create_challenge(self, challenge_data: ChallengeCreate) -> Challenge:
        # Determine initial status based on dates
        now = datetime.utcnow()
        if challenge_data.start_date > now:
            status = ChallengeStatus.UPCOMING
        elif challenge_data.end_date < now:
            status = ChallengeStatus.COMPLETED
        else:
            status = ChallengeStatus.ACTIVE

        challenge = Challenge(
            challenge_name=challenge_data.challenge_name,
            description=challenge_data.description,
            event_type=challenge_data.event_type,
            task_type=TaskType.TRANSCRIPTION if challenge_data.event_type == EventType.DATA_COLLECTION else TaskType.TRANSLATION,
            event_category=EventCategory.COMPETITION,  # Default to competition
            start_date=challenge_data.start_date,
            end_date=challenge_data.end_date,
            status=status,
            is_public=True,
            is_published=False,
            reward=challenge_data.reward
        )
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        return await self.db.get(Challenge, challenge_id)

    async def update_challenge(self, challenge_id: str, challenge_data: ChallengeUpdate) -> Optional[Challenge]:
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        update_data = challenge_data.model_dump(exclude_unset=True)

        # If dates are being updated, recalculate status
        if 'start_date' in update_data or 'end_date' in update_data:
            now = datetime.utcnow()
            start_date = update_data.get('start_date', challenge.start_date)
            end_date = update_data.get('end_date', challenge.end_date)

            if start_date > now:
                update_data['status'] = ChallengeStatus.UPCOMING
            elif end_date < now:
                update_data['status'] = ChallengeStatus.COMPLETED
            else:
                update_data['status'] = ChallengeStatus.ACTIVE

        for key, value in update_data.items():
            setattr(challenge, key, value)

        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def delete_challenge(self, challenge_id: str) -> bool:
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return False
        if challenge.status == ChallengeStatus.COMPLETED or challenge.status == ChallengeStatus.UPCOMING:
            await self.db.delete(challenge)
            await self.db.commit()
            return True
        else:
            raise ValueError("Cannot delete an active")

    async def list_challenges(self, query_params: GetChallenges) -> List[Challenge]:
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

        # Apply pagination
        query = query.offset(query_params.skip).limit(query_params.limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def publish_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Mark a challenge as published, making it visible to users"""
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        challenge.is_published = True
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def unpublish_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Mark a challenge as unpublished, hiding it from users"""
        challenge = await self.get_challenge(challenge_id)
        if not challenge:
            return None

        challenge.is_published = False
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    async def update_challenge_status(self, challenge_id: str, status: ChallengeStatus) -> Optional[Challenge]:
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
        existing_participation = await self.db.execute(
            select(ChallengeParticipation).where(
                and_(
                    ChallengeParticipation.event_id == participation_data.event_id,
                    ChallengeParticipation.user_id == participation_data.user_id
                )
            )
        )

        if existing_participation:
            raise ValueError("User is already participating in this challenge")

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

    async def leave_challenge(self, event_id: str, user_id: str) -> bool:
        """Remove a user from a challenge and decrement the participant count"""
        # Find the participation record
        participation = await self.db.execute(
            select(ChallengeParticipation).where(
                and_(
                    ChallengeParticipation.event_id == event_id,
                    ChallengeParticipation.user_id == user_id
                )
            )
        )

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

    async def get_challenge_participation(self, event_id: str,
                                          user_id: str) -> Optional[ChallengeParticipation]:
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

    async def update_participation_stats(self,
                                         event_id: str,
                                         user_id: str,
                                         stats_data: ChallengeParticipationUpdate) -> Optional[ChallengeParticipation]:
        """Update a user's statistics for a challenge"""
        participation = await self.get_challenge_participation(event_id, user_id)
        if not participation:
            return None

        update_data = stats_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(participation, key, value)

        participation.updated_at = datetime.utcnow()

        self.db.add(participation)
        await self.db.commit()
        await self.db.refresh(participation)
        return participation

    async def get_challenge_participants(self, event_id: str, skip: int = 0, limit: int = 100
                                         ) -> List[ChallengeParticipation]:
        """Get all participants for a challenge"""
        query = select(ChallengeParticipation).where(ChallengeParticipation.event_id == event_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_challenges(self, user_id: str, skip: int = 0, limit: int = 100
                                  ) -> List[ChallengeParticipation]:
        """Get all challenges a user is participating in"""
        query = select(ChallengeParticipation).where(ChallengeParticipation.user_id == user_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def increment_challenge_contribution_count(self, event_id: str) -> Optional[Challenge]:
        """Increment the contribution count for a challenge"""
        challenge = await self.get_challenge(event_id)
        if not challenge:
            return None

        challenge.contribution_count += 1
        self.db.add(challenge)
        await self.db.commit()
        await self.db.refresh(challenge)
        return challenge

    # Challenge leaderboard methods
    async def get_challenge_leaderboard(self, event_id: str, skip: int = 0, limit: int = 10
                                        ) -> List[Dict[str, Any]]:
        """Get the leaderboard for a challenge, sorted by total points"""
        # Join ChallengeParticipation with User to get usernames
        query = select(
            ChallengeParticipation, User.username, User.fullname
        ).join(
            User, ChallengeParticipation.user_id == User.id
        ).where(
            ChallengeParticipation.event_id == event_id
        ).order_by(
            desc(ChallengeParticipation.total_points)
        ).offset(skip).limit(limit)

        results = await self.db.execute(query)

        # Format the results
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

        return leaderboard

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
