from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, update, delete
from sqlalchemy.orm import selectinload  # This is the missing import
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from models.challenge import (
    Challenge,
    ChallengeParticipation,
    ChallengeStatus,
    ChallengeRule,
    EventType,
    TaskType,
    EventCategory
)
from models.user import User


# class ChallengeRepository:
#     def __init__(self, db_session: AsyncSession):
#         self.db = db_session
#
#     async def create(self, challenge_data: Dict[str, Any]) -> Challenge:
#         """Create a new challenge with automatic status determination."""
#         # Determine status based on dates
#         now = datetime.utcnow()
#         if challenge_data['end_date'] < now:
#             challenge_data['status'] = ChallengeStatus.COMPLETED
#         elif challenge_data['start_date'] <= now <= challenge_data['end_date']:
#             challenge_data['status'] = ChallengeStatus.ACTIVE
#         else:
#             challenge_data['status'] = ChallengeStatus.UPCOMING
#
#         challenge = Challenge(**challenge_data)
#         self.db.add(challenge)
#         await self.db.commit()
#         await self.db.refresh(challenge)
#         return challenge
#
#     async def get_by_id(self, challenge_id: UUID) -> Optional[Challenge]:
#         """Get challenge by ID with all relationships."""
#         result = await self.db.execute(
#             select(Challenge)
#             .where(Challenge.id == challenge_id)
#             .options(
#                 selectinload(Challenge.language),
#                 selectinload(Challenge.reward),
#                 selectinload(Challenge.participants)
#             )
#         )
#
#         return result.scalar_one_or_none()
#
#     async def get_all(
#             self,
#             skip: int = 0,
#             limit: int = 100,
#             *,
#             status: Optional[ChallengeStatus] = None,
#             event_type: Optional[EventType] = None,
#             task_type: Optional[TaskType] = None,
#             category: Optional[EventCategory] = None,
#             is_public: Optional[bool] = None,
#             is_published: Optional[bool] = None
#     ) -> List[Challenge]:
#         """Get challenges with flexible filtering."""
#         query = select(Challenge)
#
#         if status:
#             query = query.where(Challenge.status == status)
#         if event_type:
#             query = query.where(Challenge.event_type == event_type)
#         if task_type:
#             query = query.where(Challenge.task_type == task_type)
#         if category:
#             query = query.where(Challenge.event_category == category)
#         if is_public is not None:
#             query = query.where(Challenge.is_public == is_public)
#         if is_published is not None:
#             query = query.where(Challenge.is_published == is_published)
#
#         query = query.offset(skip).limit(limit)
#         result = await self.db.execute(query)
#         return list(result.scalars().all())
#
#     async def update(self, challenge_id: UUID, update_data: Dict[str, Any]) -> Optional[Challenge]:
#         """Update challenge with status recalculation if dates change."""
#         challenge = await self.get_by_id(challenge_id)
#         if not challenge:
#             return None
#
#         # Recalculate status if dates are being updated
#         if 'start_date' in update_data or 'end_date' in update_data:
#             new_start = update_data.get('start_date', challenge.start_date)
#             new_end = update_data.get('end_date', challenge.end_date)
#             now = datetime.utcnow()
#
#             if new_end < now:
#                 update_data['status'] = ChallengeStatus.COMPLETED
#             elif new_start <= now <= new_end:
#                 update_data['status'] = ChallengeStatus.ACTIVE
#             else:
#                 update_data['status'] = ChallengeStatus.UPCOMING
#
#         for key, value in update_data.items():
#             setattr(challenge, key, value)
#
#         await self.db.commit()
#         await self.db.refresh(challenge)
#         return challenge
#
#     async def delete(self, challenge_id: UUID) -> bool:
#         """Delete a challenge and its participations (cascade)."""
#         challenge = await self.get_by_id(challenge_id)
#         if challenge:
#             await self.db.delete(challenge)
#             await self.db.commit()
#             return True
#         return False
#
#     async def add_participant(self, challenge_id: UUID, user_id: UUID) -> ChallengeParticipation:
#         """Add a user to a challenge."""
#         participation = ChallengeParticipation(
#             event_id=challenge_id,
#             user_id=user_id
#         )
#         self.db.add(participation)
#
#         # Update participant count
#         await self.db.execute(
#             update(Challenge)
#             .where(Challenge.id == challenge_id)
#             .values(participant_count=Challenge.participant_count + 1)
#         )
#
#         await self.db.commit()
#         await self.db.refresh(participation)
#         return participation
#
#     async def get_challenge_participation(
#             self,
#             user_id: UUID,
#             event_id: UUID
#     ) -> Optional[ChallengeParticipation]:
#         query = select(ChallengeParticipation).where(
#             ChallengeParticipation.user_id == user_id,
#             ChallengeParticipation.event_id == event_id
#         )
#         result = await self.db.execute(query)
#         return result.scalar_one_or_none()
#
#
#
#     async def get_leaderboard(
#             self,
#             challenge_id: UUID,
#             skip: int = 0,
#             limit: int = 100
#     ) -> List[Dict[str, Any]]:
#         """Get challenge leaderboard with user details."""
#         result = await self.db.execute(
#             select(ChallengeParticipation, User)
#             .join(User, ChallengeParticipation.user_id == User.id)
#             .where(ChallengeParticipation.event_id == challenge_id)
#             .order_by(desc(ChallengeParticipation.total_points))
#             .offset(skip)
#             .limit(limit)
#         )
#
#         return [
#             {
#                 "user_id": user.id,
#                 "username": user.username,
#                 "points": participation.total_points,
#                 "stats": {
#                     "hours_speech": participation.total_hours_speech,
#                     "sentences_translated": participation.total_sentences_translated,
#                     "tokens_produced": participation.total_tokens_produced,
#                     "acceptance_rate": participation.acceptance_rate
#                 }
#             }
#             for participation, user in result.all()
#         ]
#
#     async def update_challenge_statuses(self):
#         """Batch update challenge statuses based on current time."""
#         now = datetime.utcnow()
#
#         # Update completed challenges
#         await self.db.execute(
#             update(Challenge)
#             .where(Challenge.end_date < now)
#             .values(status=ChallengeStatus.COMPLETED)
#         )
#
#         # Update active challenges
#         await self.db.execute(
#             update(Challenge)
#             .where(
#                 Challenge.start_date <= now,
#                 Challenge.end_date >= now
#             )
#             .values(status=ChallengeStatus.ACTIVE)
#         )
#
#         # Update upcoming challenges
#         await self.db.execute(
#             update(Challenge)
#             .where(Challenge.start_date > now)
#             .values(status=ChallengeStatus.UPCOMING)
#         )
#
#         await self.db.commit()
#

class ChallengeRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_rule(self, challenge_id: UUID, rule_data: dict):
        rule = ChallengeRule(**rule_data, challenge_id=challenge_id)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_rules(self, challenge_id: UUID):
        result = await self.db.execute(
            select(ChallengeRule)
            .where(ChallengeRule.challenge_id == challenge_id)
        )
        return result.scalars().all()

    async def update_rule(
            self,
            rule_id: UUID,
            update_data: dict
    ) -> Optional[ChallengeRule]:
        """Update an existing rule"""
        result = await self.db.execute(
            select(ChallengeRule)
            .where(ChallengeRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if rule:
            for key, value in update_data.items():
                setattr(rule, key, value)
            rule.updated_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(rule)

        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a specific rule"""
        result = await self.db.execute(
            delete(ChallengeRule)
            .where(ChallengeRule.id == rule_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def add_rules(self, challenge_id: UUID, rules_data: List[ChallengeRule]) -> List[ChallengeRule]:
        """Add multiple rules to a challenge"""
        rules = [ChallengeRule(
            **rule.model_dump(exclude_unset=True),
            challenge_id=challenge_id
        )
            for rule in rules_data]

        self.db.add_all(rules)
        await self.db.commit()
        return rules

    async def delete_all_challenge_rules(self, challenge_id: UUID) -> bool:
        """Delete all rules for a specific challenge"""
        result = await self.db.execute(
            delete(ChallengeRule)
            .where(ChallengeRule.challenge_id == challenge_id)
        )
        await self.db.commit()
        val = len(result.all()) > 0
        return val
