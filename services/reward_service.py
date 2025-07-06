from typing import List, Optional
import uuid
import logging
from datetime import datetime, timezone
from crud.rewards import RewardsCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from models.rewards import (
    Milestone, UserMilestone,
    ChallengeReward, UserChallengeReward
)
from schemas.rewards import (
    MilestoneCreate, MilestoneUpdate, UserMilestoneCreate, UserChallengeRewardCreate,
    GetRewards, ChallengeRewardUpdate
)

from services.challenge_service import ChallengeService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('rewards_service.log')
    ]
)
logger = logging.getLogger("rewards_service")


class RewardsService:
    """
    Service class handling business logic related to rewards
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.crud = RewardsCRUD(db)

    # Business logic methods for Milestone
    async def create_milestone(self, milestone_data: MilestoneCreate) -> Milestone:
        logger.info(f"Creating new milestone: {milestone_data.name}")
        return await self.crud.create_milestone(milestone_data)

    async def get_milestone(self, milestone_id: uuid.UUID) -> Optional[Milestone]:
        return await self.crud.get_milestone(milestone_id)

    async def update_milestone(self, milestone_id: uuid.UUID, milestone_data: MilestoneUpdate) -> Optional[Milestone]:
        logger.info(f"Updating milestone {milestone_id}")
        return await self.crud.update_milestone(milestone_id, milestone_data)

    async def delete_milestone(self, milestone_id: uuid.UUID) -> bool:
        logger.info(f"Deleting milestone {milestone_id}")
        return await self.crud.delete_milestone(milestone_id)

    async def list_milestones(self) -> List[Milestone]:
        return await self.crud.list_milestones()

    # Business logic methods for User Milestone
    async def award_milestone(self, user_milestone_data: UserMilestoneCreate) -> UserMilestone:
        logger.info(f"Awarding milestone {user_milestone_data.milestone_id} to user {user_milestone_data.user_id}")

        # Check if milestone exists
        milestone = await self.crud.get_milestone(uuid.UUID(user_milestone_data.milestone_id))
        if not milestone:
            logger.warning(f"Cannot award non-existent milestone {user_milestone_data.milestone_id}")
            raise ValueError(f"Milestone with ID {user_milestone_data.milestone_id} not found")

        # Check if user already has this milestone
        existing_milestones = await self.crud.get_user_milestones(uuid.UUID(user_milestone_data.user_id))
        for existing in existing_milestones:
            if existing.milestone_id == user_milestone_data.milestone_id:
                logger.warning(
                    f"User {user_milestone_data.user_id} already has milestone {user_milestone_data.milestone_id}")
                return existing

        # If no achieved_at date is set, use current time
        if not user_milestone_data.achieved_at:
            user_milestone_data.achieved_at = datetime.now(timezone.utc)

        return await self.crud.create_user_milestone(user_milestone_data)

    async def get_user_milestone(self, user_milestone_id: uuid.UUID) -> Optional[UserMilestone]:
        return await self.crud.get_user_milestone(user_milestone_id)

    async def get_user_milestones(self, user_id: uuid.UUID) -> List[UserMilestone]:
        return await self.crud.get_user_milestones(user_id)

    async def delete_user_milestone(self, user_milestone_id: uuid.UUID) -> bool:
        logger.info(f"Deleting user milestone {user_milestone_id}")
        return await self.crud.delete_user_milestone(user_milestone_id)

    # Business logic methods for Challenge Reward
    async def create_challenge_reward(self, reward_data: ChallengeRewardUpdate) -> ChallengeReward:
        logger.info(f"Creating challenge reward of type {reward_data.reward_type}")
        return await self.crud.create_challenge_reward(reward_data)

    async def get_challenge_reward(self, reward_id: uuid.UUID) -> Optional[ChallengeReward]:
        return await self.crud.get_challenge_reward(reward_id)

    async def update_challenge_reward(
            self, reward_id: uuid.UUID,
            reward_data: ChallengeRewardUpdate,
            challenge_id: Optional[uuid.UUID] = None
    ) -> Optional[ChallengeReward]:
        logger.info(f"Updating challenge reward {reward_id}")

        reward = await self.crud.get_challenge_reward(reward_id)
        if not reward:
            logger.warning(f"Reward with ID {reward_id} not found")
            return None

        # Business logic check: Can't update reward for published challenge
        if challenge_id:
            challenge_service = ChallengeService(self.db)
            published = await challenge_service.is_published(challenge_id)

            if published:
                logger.warning(f"Cannot update reward {reward_id} for published challenge {challenge_id}")
                raise Exception("Cannot update a published challenge reward")

        return await self.crud.update_challenge_reward_raw(reward_id, reward_data)

    async def delete_challenge_reward(self, reward_id: uuid.UUID) -> bool:
        logger.info(f"Deleting challenge reward {reward_id}")
        return await self.crud.delete_challenge_reward(reward_id)

    async def list_challenge_rewards(self, query_params: GetRewards) -> List[ChallengeReward]:
        return await self.crud.list_challenge_rewards(
            skip=query_params.skip,
            limit=query_params.limit,
            reward_type=query_params.reward_type
        )

    # Business logic methods for User Challenge Reward
    async def award_challenge_reward(self, award_data: UserChallengeRewardCreate) -> UserChallengeReward:
        logger.info(f"Awarding challenge reward {award_data.reward_id} to user {award_data.user_id}")

        # Check if reward exists
        reward = await self.crud.get_challenge_reward(award_data.reward_id)
        if not reward:
            logger.warning(f"Cannot award non-existent reward {award_data.reward_id}")
            raise ValueError(f"Reward with ID {award_data.reward_id} not found")

        # If no awarded_at date is set, use current time
        if not award_data.awarded_at:
            award_data.awarded_at = datetime.now(timezone.utc)

        return await self.crud.create_user_challenge_reward(award_data)  

    async def get_user_challenge_rewards(self, user_id: uuid.UUID) -> List[UserChallengeReward]:
        return await self.crud.get_user_challenge_rewards(user_id)

    async def get_challenge_rewards_by_challenge(self, challenge_id: uuid.UUID) -> List[UserChallengeReward]:
        return await self.crud.get_challenge_rewards_by_challenge(challenge_id)