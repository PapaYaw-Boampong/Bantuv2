from typing import List, Optional
import uuid
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.rewards import (
    Milestone, UserMilestone,
    ChallengeReward, UserChallengeReward, RewardType
)
from schemas.rewards import (
    MilestoneCreate, MilestoneUpdate, UserMilestoneCreate,
    ChallengeRewardCreate, UserChallengeRewardCreate,
    GetRewards, ChallengeRewardUpdate
)

from services.challenge_service import ChallengeService


class RewardsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Milestone methods
    async def create_milestone(self, milestone_data: MilestoneCreate) -> Milestone:
        milestone = Milestone(
            name=milestone_data.name,
            description=milestone_data.description,
            reward_type=milestone_data.reward_type,
            reward_value=milestone_data.reward_value,
            required_actions=milestone_data.required_actions
        )
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def get_milestone(self, milestone_id: uuid.UUID) -> Optional[Milestone]:
        return await self.db.get(Milestone, milestone_id)

    async def update_milestone(self, milestone_id: uuid.UUID, milestone_data: MilestoneUpdate) -> Optional[Milestone]:
        milestone = await self.get_milestone(milestone_id)
        if not milestone:
            return None

        update_data = milestone_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(milestone, key, value)

        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def delete_milestone(self, milestone_id: uuid.UUID) -> bool:
        milestone = await self.get_milestone(milestone_id)
        if not milestone:
            return False

        await self.db.delete(milestone)
        await self.db.commit()
        return True

    async def list_milestones(self) -> List[Milestone]:
        query = select(Milestone)
        result = await self.db.execute(query)  # Awaiting the execution of the query
        return list(result.scalars().all())

        # User Milestone methods

    async def award_milestone(self, user_milestone_data: UserMilestoneCreate) -> UserMilestone:
        user_milestone = UserMilestone(
            user_id=user_milestone_data.user_id,
            milestone_id=user_milestone_data.milestone_id,
            achieved_at=user_milestone_data.achieved_at
        )
        self.db.add(user_milestone)
        await self.db.commit()
        await self.db.refresh(user_milestone)
        return user_milestone

    async def get_user_milestone(self, user_milestone_id: uuid) -> Optional[UserMilestone]:
        return await self.db.get(UserMilestone, user_milestone_id)

    async def get_user_milestones(self, user_id: uuid.UUID) -> List[UserMilestone]:
        query = select(UserMilestone).where(UserMilestone.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_user_milestone(self, user_milestone_id: uuid) -> bool:
        user_milestone = await self.get_user_milestone(user_milestone_id)
        if not user_milestone:
            return False

        await self.db.delete(user_milestone)
        await self.db.commit()
        return True

    # Challenge Reward methods
    async def create_challenge_reward(
            self,
            reward_data: ChallengeRewardUpdate
    ) -> ChallengeReward:
        reward = ChallengeReward(
            reward_type=reward_data.reward_type,
            reward_value=reward_data.reward_value,
            reward_distribution_type=reward_data.reward_distribution_type
        )
        self.db.add(reward)
        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def get_challenge_reward(
            self, reward_id: uuid.UUID
    ) -> Optional[ChallengeReward]:
        return await self.db.get(ChallengeReward, reward_id)

    async def update_challenge_reward(
            self, reward_id: uuid.UUID,
            reward_data: ChallengeRewardUpdate
    ) -> Optional[ChallengeReward]:
        reward = await self.get_challenge_reward(reward_id)
        if not reward:
            return None

        challenge_service = ChallengeService(self.db)
        published = await challenge_service.is_published(reward.challenge_id)

        if published:
            raise Exception("Cannot update a published challenge reward")

        update_data = reward_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(reward, key, value)

        self.db.add(reward)
        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def delete_challenge_reward(self, reward_id: uuid.UUID) -> bool:
        reward = await self.get_challenge_reward(reward_id)
        if not reward:
            return False

        await self.db.delete(reward)
        await self.db.commit()
        return True

    async def list_challenge_rewards(self, query_params: GetRewards) -> List[ChallengeReward]:
        query = select(ChallengeReward)

        if query_params.reward_type:
            query = query.where(ChallengeReward.reward_type == query_params.reward_type)

        query = query.offset(query_params.skip).limit(query_params.limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # User Challenge Reward methods
    async def award_challenge_reward(self, award_data: UserChallengeRewardCreate) -> UserChallengeReward:
        award = UserChallengeReward(
            user_id=award_data.user_id,
            reward_id=award_data.reward_id,
            challenge_id=award_data.challenge_id,
            awarded_at=award_data.awarded_at
        )
        self.db.add(award)
        await self.db.commit()
        await self.db.refresh(award)
        return award

    async def get_user_challenge_rewards(self, user_id: str) -> List[UserChallengeReward]:
        query = select(UserChallengeReward).where(UserChallengeReward.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_challenge_rewards_by_challenge(self, challenge_id: str) -> List[UserChallengeReward]:
        query = select(UserChallengeReward).where(UserChallengeReward.challenge_id == challenge_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
