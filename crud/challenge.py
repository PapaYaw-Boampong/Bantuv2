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


class ChallengeRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_rule(self, challenge_id: UUID, rule_data: ChallengeRule) -> ChallengeRule:
        rule_dict = rule_data.model_dump(exclude_unset=True)  # Convert Pydantic model to dict
        rule = ChallengeRule(**rule_dict, challenge_id=challenge_id)
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
