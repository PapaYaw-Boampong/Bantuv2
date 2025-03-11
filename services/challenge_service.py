from typing import List, Dict, Any, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime
from models.challenge import Challenge, ChallengeParticipation, EventType
from crud.challenge import ChallengeCRUD


class ChallengeService:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session
        self.crud = ChallengeCRUD(db_session)

    async def create_challenge(self, challenge_data: Dict[str, Any]) -> Challenge:
        """Create a new challenge."""
        return await self.crud.create_challenge(challenge_data)

    async def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a specific challenge by ID."""
        return await self.crud.get_challenge(challenge_id)

    async def get_active_challenges(self, skip: int = 0, limit: int = 100) -> List[Challenge]:
        """Get all active challenges."""
        return await self.crud.get_challenges(skip=skip, limit=limit, active_only=True)

    async def get_all_challenges(self, skip: int = 0, limit: int = 100) -> List[Challenge]:
        """Get all challenges."""
        return await self.crud.get_challenges(skip=skip, limit=limit)

    async def update_challenge(self, challenge_id: str, challenge_data: Dict[str, Any]) -> Optional[Challenge]:
        """Update challenge information."""
        return await self.crud.update_challenge(challenge_id, challenge_data)

    async def get_leaderboard(self, challenge_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top participants for a challenge."""
        return await self.crud.get_challenge_participants(
            challenge_id=challenge_id,
            limit=limit
        )

    async def register_user_to_challenge(self, challenge_id: str, user_id: str) -> Dict[str, Any]:
        """Register a user to a challenge."""
        # Check if the challenge exists
        challenge = await self.crud.get_challenge(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge with ID {challenge_id} not found")

        # Check if the user is already registered
        user_stats = await self.crud.get_user_challenge_stats(challenge_id, user_id)
        if user_stats:
            return user_stats

        # Create new participation entry
        participation = ChallengeParticipation(
            event_id=challenge_id,
            user_id=user_id
        )

        self.db.add(participation)
        await self.db.commit()
        await self.db.refresh(participation)

        # Update challenge stats
        await self.crud.update_challenge_stats(challenge_id)

        # Return updated stats
        return await self.crud.get_user_challenge_stats(challenge_id, user_id)

    async def update_user_stats(self,
                                challenge_id: str,
                                user_id: str,
                                stats_update: Dict[str, Any],
                                update_points: bool = False) -> Dict[str, Any]:
        """Update user statistics for a specific challenge."""
        # Find the participation record
        statement = select(ChallengeParticipation).where(
            ChallengeParticipation.event_id == challenge_id,
            ChallengeParticipation.user_id == user_id
        )
        result = await self.db.exec(statement)

        if update_points:
            stats_update['total_points'] = self._calculate_points(result)

        participation = result.scalar_one_or_none()

        if not participation:
            raise ValueError(f"User {user_id} is not registered for challenge {challenge_id}")

        # Update the stats
        for key, value in stats_update.items():
            if hasattr(participation, key):
                setattr(participation, key, value)

        # Calculate points based on the metrics
        participation.total_points = self._calculate_points(participation)
        participation.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(participation)

        # Update challenge overall stats
        await self.crud.update_challenge_stats(challenge_id)

        # Return updated user stats
        return await self.crud.get_user_challenge_stats(challenge_id, user_id)

    @staticmethod
    def _calculate_points(participation: ChallengeParticipation) -> int:
        """Calculate points based on user's contributions."""
        # Points calculation logic based on the type of challenge
        challenge_type = participation.event.EventType

        # Base points
        points = 0

        # Points for speech hours (important for transcription challenges)
        points += participation.total_hours_speech * 10

        # Points for translated sentences (important for translation challenges)
        points += participation.total_sentences_translated * 2

        # Points for tokens produced (general metric)
        points += participation.total_tokens_produced * 0.1

        # Bonus for high acceptance rate
        if participation.acceptance_rate > 0.9:
            points *= 1.2
        elif participation.acceptance_rate > 0.8:
            points *= 1.1

        # Adjust points based on challenge type
        if challenge_type == EventType.TRANSCRIPTION_CHALLENGE:
            # Prioritize hours of speech for transcription challenges
            points += participation.total_hours_speech * 15
        elif challenge_type == EventType.TRANSLATION_SPRINT:
            # Prioritize translated sentences for translation challenges
            points += participation.total_sentences_translated * 3
        elif challenge_type == EventType.CORRECTION_MARATHON:
            # Prioritize acceptance rate for correction challenges
            points += participation.acceptance_rate * 100

        return int(points)

    async def get_challenge_summary(self) -> List[Dict[str, Any]]:
        """Get summarized information about all challenges."""
        return await self.crud.get_challenge_summary()

    async def end_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Mark a challenge as inactive and finalize statistics."""
        challenge = await self.crud.get_challenge(challenge_id)
        if not challenge:
            return None

        # Update the challenge to inactive
        update_data = {
            "is_active": False,
            "end_date": datetime.utcnow()
        }

        # Final update of statistics
        await self.crud.update_challenge_stats(challenge_id)

        # Update the challenge
        return await self.crud.update_challenge(challenge_id, update_data)
