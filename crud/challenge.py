from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, desc
from typing import List, Optional, Dict, Any
from models.challenge import Challenge, ChallengeParticipation
from models.user import User


class ChallengeCRUD:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_challenge(self, challenge_data: Dict[str, Any]) -> Challenge:
        """Create a new challenge."""
        async with self.db.begin():
            challenge = Challenge(**challenge_data)
            self.db.add(challenge)
            await self.db.flush()  # Ensures the object gets an ID before commit
            await self.db.refresh(challenge)
        return challenge

    async def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get a specific challenge by ID with all details."""
        result = await self.db.execute(
            select(Challenge).where(Challenge.id == challenge_id)
        )
        return result.scalar_one_or_none()

    async def get_challenges(
            self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[Challenge]:
        """Get all challenges with pagination."""
        query = select(Challenge)
        if active_only:
            query = query.where(Challenge.is_active == True)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_challenge(
            self, challenge_id: str, challenge_data: Dict[str, Any]
    ) -> Optional[Challenge]:
        """Update challenge information."""
        result = await self.db.execute(
            select(Challenge).where(Challenge.id == challenge_id)
        )
        challenge = result.scalar_one_or_none()

        if challenge:
            for key, value in challenge_data.items():
                setattr(challenge, key, value)

            async with self.db.begin():
                await self.db.flush()
                await self.db.refresh(challenge)

        return challenge

    async def delete_challenge(self, challenge_id: str) -> bool:
        """Delete a challenge."""
        result = await self.db.execute(
            select(Challenge).where(Challenge.id == challenge_id)
        )
        challenge = result.scalar_one_or_none()

        if challenge:
            async with self.db.begin():
                await self.db.delete(challenge)
                await self.db.flush()
            return True
        return False

    async def get_challenge_summary(self) -> List[Dict[str, Any]]:
        """Get summarized info for all challenges."""
        result = await self.db.execute(
            select([
                Challenge.id,
                Challenge.challenge_name,
                Challenge.EventType,
                Challenge.start_date,
                Challenge.end_date,
                Challenge.is_active,
                Challenge.participant_count,
                Challenge.contribution_count,
            ])
        )
        challenges = result.all()

        return [
            {
                "id": c.id,
                "name": c.challenge_name,
                "type": c.EventType,
                "start_date": c.start_date,
                "end_date": c.end_date,
                "is_active": c.is_active,
                "participant_count": c.participant_count,
                "contribution_count": c.contribution_count,
            }
            for c in challenges
        ]

    async def get_challenge_participants(
            self, challenge_id: str, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get participants of a challenge with their stats, sorted by points."""
        result = await self.db.execute(
            select(ChallengeParticipation, User)
            .where(
                ChallengeParticipation.event_id == challenge_id,
                ChallengeParticipation.user_id == User.id,
            )
            .order_by(desc(ChallengeParticipation.total_points))
            .offset(skip)
            .limit(limit)
        )

        participants = result.all()

        return [
            {
                "user_id": user.id,
                "username": user.username,
                "name": f"{user.first_name} {user.last_name}",
                "points": participation.total_points,
                "hours_speech": participation.total_hours_speech,
                "sentences_translated": participation.total_sentences_translated,
                "tokens_produced": participation.total_tokens_produced,
                "acceptance_rate": participation.acceptance_rate,
            }
            for participation, user in participants
        ]

    async def get_user_challenge_stats(
            self, challenge_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get stats for a specific user in a specific challenge."""
        result = await self.db.execute(
            select(ChallengeParticipation, User).where(
                ChallengeParticipation.event_id == challenge_id,
                ChallengeParticipation.user_id == user_id,
                ChallengeParticipation.user_id == User.id,
            )
        )
        participation_and_user = result.first()

        if not participation_and_user:
            return None

        participation, user = participation_and_user

        return {
            "user_id": user.id,
            "username": user.username,
            "name": f"{user.first_name} {user.last_name}",
            "points": participation.total_points,
            "hours_speech": participation.total_hours_speech,
            "sentences_translated": participation.total_sentences_translated,
            "tokens_produced": participation.total_tokens_produced,
            "acceptance_rate": participation.acceptance_rate,
            "created_at": participation.created_at,
            "updated_at": participation.updated_at,
        }

    async def get_users_challenge_stats(
            self, challenge_id: str, user_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get stats for multiple users in a specific challenge."""
        result = await self.db.execute(
            select(ChallengeParticipation, User).where(
                ChallengeParticipation.event_id == challenge_id,
                ChallengeParticipation.user_id.in_(user_ids),
                ChallengeParticipation.user_id == User.id,
            )
        )
        participants = result.all()

        return [
            {
                "user_id": user.id,
                "username": user.username,
                "name": f"{user.first_name} {user.last_name}",
                "points": participation.total_points,
                "hours_speech": participation.total_hours_speech,
                "sentences_translated": participation.total_sentences_translated,
                "tokens_produced": participation.total_tokens_produced,
                "acceptance_rate": participation.acceptance_rate,
            }
            for participation, user in participants
        ]

    async def update_challenge_stats(self, challenge_id: str) -> Optional[Challenge]:
        """Update challenge statistics based on participant data."""
        result = await self.db.execute(
            select(Challenge).where(Challenge.id == challenge_id)
        )
        challenge = result.scalar_one_or_none()

        if not challenge:
            return None

        participant_result = await self.db.execute(
            select(ChallengeParticipation).where(
                ChallengeParticipation.event_id == challenge_id
            )
        )
        participants = participant_result.scalars().all()

        # Update challenge statistics
        challenge.participant_count = len(participants)
        challenge.contribution_count = sum(p.total_sentences_translated for p in participants)

        async with self.db.begin():
            await self.db.flush()
            await self.db.refresh(challenge)

        return challenge
