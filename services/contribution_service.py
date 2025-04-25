import uuid
from random import choice
from typing import Dict, List, Optional, Union, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from sqlalchemy.orm import selectinload
from datetime import datetime
from services.language_service import LanguageService

from core.config import settings
from models import (
    AnnotationContribution,
    TranscriptionContribution,
    TranslationContribution,
    AnnotationSample,
    TranscriptionSample,
    TranslationSample,
)

from schemas.contribution import (
    ContributionCreate,
    ContributionUpdate,
    ContributionFilter,
    ContributionStats,
    CustomContributionCreate
)

from schemas.sample_data import (
    TranscriptionSampleCreate,
    TranslationSampleCreate,
    AnnotationSampleCreate,
    AnnotationSeedCreate,
    TranslationSeedCreate
)


from schemas.challenge import ParticipationUpdate


class ContributionManagementService:
    """
    Service responsible for overseeing, distributing, and validating user contributions
    across different task types (transcription, translation, annotation).
    Acts as an intelligent router and state manager for contributions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.contribution_types = {
            "annotation": AnnotationContribution,
            "transcription": TranscriptionContribution,
            "translation": TranslationContribution
        }
        self.sample_types = {
            "annotation": AnnotationSample,
            "transcription": TranscriptionSample,
            "translation": TranslationSample
        }

    async def _get_model_class(self, contribution_type: str) -> Type:
        """Get the appropriate model class based on contribution type"""
        if contribution_type not in self.contribution_types:
            raise ValueError(f"Invalid contribution type: {contribution_type}")
        return self.contribution_types[contribution_type]

    async def _get_sample_class(self, contribution_type: str) -> Type:
        """Get the appropriate sample class based on contribution type"""
        if contribution_type not in self.sample_types:
            raise ValueError(f"Invalid contribution type: {contribution_type}")
        return self.sample_types[contribution_type]

    # =========== Create Operations ==========
    async def create_contribution(
            self,
            challenge_id: Optional[uuid.UUID],
            user_id: uuid.UUID,
            contribution_type: str,
            sample_id: uuid.UUID,
            language_id: uuid.UUID,
            data: ContributionCreate
    ) -> Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]:
        """Create a new contribution of the specified type"""
        model_class = await self._get_model_class(contribution_type)
        # Common fields
        contribution_data = {
            "user_id": user_id,
            "sample_id": sample_id,
            "created_at": datetime.utcnow(),
            "active": True,
            "flagged": False,
            "passed": False,
            "upvotes": 1
        }

        language_service = LanguageService(self.db)
        from services.challenge_service import ChallengeService
        challenge_service = ChallengeService(self.db)

        word_dict = {}
        stats_data = ParticipationUpdate(
            is_contribution=True,
        )

        if data.target_text == "" and data.target_url == "":
            raise ValueError("Contribution cannot be empty")

        # Type-specific fields
        if contribution_type in {"annotation", "translation"}:
            contribution_data["target_text"] = data.target_text
            word_list = data.target_text.strip().lower().split()
            for word in word_list:
                word_dict[word] = word_dict.get(word, 0) + 1

            if contribution_type == "annotation":
                token_count = len(word_list)
                stats_data.total_tokens_produced = token_count

            elif contribution_type == "translation":
                stats_data.total_sentences_translated = 1

        elif contribution_type == "transcription":
            contribution_data["target_url"] = data.target_url
            stats_data.total_hours_speech = data.speech_length

        # Save Contribution
        contribution = model_class(**contribution_data)
        self.db.add(contribution)
        await self.db.commit()
        await self.db.refresh(contribution)

        # Record contribution stats for challenge or globally
        if challenge_id:
            stats_data.total_points = settings.POINTS_PER_CONTRIBUTION
            await challenge_service.update_participation_stats(
                event_id=challenge_id,
                user_id=user_id,
                stats_data=stats_data
            )

        await language_service.user_language_repository.update_language_stats(
            user_id=user_id,
            language_id=language_id,
            stats_data=stats_data
        )

        from services.sample_data_service import SampleDataService

        # Update sample with contribution metadata
        if contribution_type in {"annotation", "translation"}:
            sample_service = SampleDataService(self.db)
            await sample_service.update_sample_with_contribution(
                sample_id=sample_id,
                sample_type=contribution_type,
                new_words=word_dict
            )

        return contribution

    # =========== Read Operations ==========
    async def get_contribution(
            self,
            contribution_id: uuid.UUID,
            contribution_type: str
    ) -> Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]:
        """Get a specific contribution by ID and type"""
        model_class = await self._get_model_class(contribution_type)

        stmt = select(model_class).where(model_class.id == contribution_id)
        result = await self.db.execute(stmt)
        contribution: Union[AnnotationContribution, TranscriptionContribution, TranslationContribution] = result.scalars().first()

        if not contribution:
            raise ValueError(f"{contribution_type.capitalize()} contribution with ID {contribution_id} not found")

        return contribution

    async def list_contributions(
            self,
            contribution_type: str,
            filters: ContributionFilter,
            skip: int = 0,
            limit: int = 100
    ) -> List[Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]]:
        """List contributions with optional filtering"""
        model_class = await self._get_model_class(contribution_type)

        # Build query
        query = select(model_class)

        # Apply filters
        if filters:
            if filters.user_id:
                query = query.where(model_class.user_id == filters.user_id)
            if filters.sample_id:
                query = query.where(model_class.sample_id == filters.sample_id)
                if filters.flagged is not None:
                    query = query.where(model_class.flagged == filters.flagged)
                if filters.passed is not None:
                    query = query.where(model_class.passed == filters.passed)
                if filters.min_upvotes is not None:
                    query = query.where(model_class.upvotes >= filters.min_upvotes)
                if filters.created_after:
                    query = query.where(model_class.created_at >= filters.created_after)
                if filters.created_before:
                    query = query.where(model_class.created_at <= filters.created_before)
                if filters.evaluation_instance_id:
                    query = query.where(model_class.evaluation_instance_id <= filters.evaluation_instance_id)

        # Add pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_contributions(
            self,
            user_id: uuid.UUID,
            contribution_type: Optional[str] = None,
            active_only: bool = True
    ) -> Dict[str, List]:
        """Get all contributions by a specific user, optionally filtered by type"""
        result = {}

        types_to_fetch = [contribution_type] if contribution_type else self.contribution_types.keys()

        for ctype in types_to_fetch:
            model_class = await self._get_model_class(ctype)
            query = select(model_class).where(model_class.user_id == user_id)

            if active_only:
                query = query.where(model_class.active == True)

            db_result = await self.db.execute(query)
            contributions = db_result.scalars().all()

            result[ctype] = contributions

        return result if contribution_type is None else result[contribution_type]

        # =========== Update Operations ==========

    async def update_contribution(
            self,
            contribution_id: uuid.UUID,
            contribution_type: str,
            data: ContributionUpdate
    ) -> Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]:
        """Update a specific contribution"""
        contribution = await self.get_contribution(contribution_id, contribution_type)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(contribution, key, value)

        await self.db.commit()
        await self.db.refresh(contribution)

        return contribution

    async def mark_as_passed(
            self,
            contribution_id: uuid.UUID,
            contribution_type: str
    ) -> None:
        """Mark a contribution as passed validation"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.passed = True
        await self.db.commit()

    async def flag_contribution(
            self, contribution_id: uuid.UUID,
            contribution_type: str
    ) -> None:
        """Flag a contribution for review"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.flagged = True
        await self.db.commit()

    async def toggle_active_state(
            self, contribution_id: uuid.UUID,
            contribution_type: str, active: bool
    ) -> None:
        """Toggle the active state of a contribution"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.active = active
        await self.db.commit()

    async def upvote_contribution(
            self, contribution_id: uuid.UUID,
            contribution_type: str
    ) -> int:
        """Add an upvote to a contribution and return new upvote count"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.upvotes += 1
        await self.db.commit()
        return contribution.upvotes

        # =========== Delete Operations ==========

    async def delete_contribution(
            self, contribution_id: uuid.UUID,
            contribution_type: str
    ) -> bool:
        """Delete a contribution (soft delete by setting active=False)"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.active = False
        await self.db.commit()
        return True

        # =========== Stats and Analysis ==========

    async def get_contribution_stats(
            self,
            user_id: Optional[uuid.UUID] = None,
            contribution_type: Optional[str] = None
    ) -> ContributionStats:
        """Get statistics about contributions"""
        stats = ContributionStats(
            total_contributions=0,
            passed_contributions=0,
            flagged_contributions=0,
            contribution_counts={},
            user_ranking=None
        )

        types_to_analyze = [contribution_type] if contribution_type else self.contribution_types.keys()

        for ctype in types_to_analyze:
            model_class = await self._get_model_class(ctype)

            # Base query
            base_query = select(model_class)
            if user_id:
                base_query = base_query.where(model_class.user_id == user_id)

            # Total count
            count_query = select(func.count()).select_from(base_query.subquery())
            result = await self.db.execute(count_query)
            count = result.scalar() or 0

            stats.total_contributions += count
            stats.contribution_counts[ctype] = count

            # Passed count
            passed_query = select(func.count()).select_from(
                base_query.where(model_class.passed == True).subquery()
            )
            result = await self.db.execute(passed_query)
            passed_count = result.scalar() or 0
            stats.passed_contributions += passed_count

            # Flagged count
            flagged_query = select(func.count()).select_from(
                base_query.where(model_class.flagged == True).subquery()
            )
            result = await self.db.execute(flagged_query)
            flagged_count = result.scalar() or 0
            stats.flagged_contributions += flagged_count

        # Calculate user ranking based on accepted contributions if user_id is provided
        if user_id:
            for ctype in types_to_analyze:
                model_class = await self._get_model_class(ctype)

                # Filter for only accepted contributions
                accepted_query = (
                    select(model_class.user_id, func.count().label('count'))
                    .where(model_class.accepted == True)
                    .group_by(model_class.user_id)
                    .order_by(desc('count'))
                )

                result = await self.db.execute(accepted_query)
                user_rankings = result.all()

                # Find position of user in rankings
                for position, (ranked_user_id, _) in enumerate(user_rankings, 1):
                    if ranked_user_id == user_id:
                        stats.user_ranking = position
                        break

        return stats

    # =========== Integration with other services ==========
    async def find_samples_for_user(
            self,
            user_id: uuid.UUID,
            contribution_type: str,
            language_id: uuid.UUID,
            limit: int = 1

    ) -> List[uuid.UUID]:
        """
            Assign a sample to a user for contribution
        """
        sample_class = await self._get_sample_class(contribution_type)

        # Build query to find available samples
        # (samples without contributions from this user)
        contribution_class = await self._get_model_class(contribution_type)

        # Get width setting based on contribution type
        width_settings = {
            "annotation": settings.ANNOTATION_BASE_WIDTH,
            "transcription": settings.TRANSCRIPTION_BASE_WIDTH,
            "translation": settings.TRANSLATION_BASE_WIDTH
        }

        if contribution_type not in width_settings:
            raise ValueError(f"Unsupported contribution type: {contribution_type}")
        width = width_settings[contribution_type]

        # Find sample IDs that the user has already contributed to
        user_contributed_subquery = (
            select(getattr(contribution_class, "sample_id"))
            .where(contribution_class.user_id == user_id)
            .subquery()
        )

        # Select a sample that hasn't been contributed to by this user
        query = (
            select(getattr(sample_class, "id"))
            .where(sample_class.id.not_in(select(user_contributed_subquery.c.sample_id)))
            .where(sample_class.active == False)
            .where(sample_class.store < width)
            .where(sample_class.language_id == language_id)
        )

        result = await self.db.execute(query)
        samples = result.scalars()

        if not result:
            raise ValueError(f"No available {contribution_type} samples found for user")

        # Randomly select from available samples up to the limit
        selected_samples = [choice(samples) for _ in range(min(limit, len(samples)))]
        return selected_samples

    async def validate_contribution(
            self,
            contribution_id: uuid.UUID,
            contribution_type: str
    ) -> bool:
        """
        Validate a contribution (integration point with Evaluation Service)
        This is a placeholder for integration with your evaluation service
        """
        # In a real implementation, this would call your evaluation service
        # For now, we'll just mark it as passed
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.passed = True
        await self.db.commit()
        return True

    async def award_points_for_contribution(
            self,
            contribution_id: uuid.UUID,
            contribution_type: str,
            points: int = 10
    ) -> None:
        """
        Award points to a user for their contribution (integration with Reward System)
        This is a placeholder for integration with your reward system
        """
        # In a real implementation, this would call your reward service
        # For now, we'll just log a message
        contribution = await self.get_contribution(contribution_id, contribution_type)
        print(f"Awarded {points} points to user {contribution.user_id} for {contribution_type} contribution")

    # =========== Custom Contribution Creation ==========

    async def create_custom_contribution(
            self,
            user_id: uuid.UUID,
            language_id: uuid.UUID,
            contribution_data: CustomContributionCreate,
            contribution_type: str,
            challenge_id: Optional[uuid.UUID] = None
    ) -> Dict:
        """
        Handle custom contributions by creating the appropriate seed and sample,
        then delegate to `create_contribution` for final processing.
        """
        seed_id = None
        from services.sample_data_service import SampleDataService

        samples_repo = SampleDataService(self.db)

        if contribution_type == "transcription":
            transcription_sample = TranscriptionSampleCreate(
                language_id=language_id,
                transcription_text=contribution_data['transcription_text'],
                category=contribution_data.get('category', None),
                active=contribution_data.get('active', False),
                priority=contribution_data.get('priority', 0),
            )
            sample = await samples_repo.create_transcription_sample(transcription_sample)
            sample_id = sample.id

            # Prepare payload
            contribution_payload = ContributionCreate(
                target_url=contribution_data['target_url'],  # or whichever audio to start with
                language_id=language_id,
                speech_length=contribution_data.get("speech_length", 0.0)
            )

        elif contribution_type == "translation":
            seed = TranslationSeedCreate(
                original_text=contribution_data['original_text'],
                category=contribution_data.get('category', None),
                active=contribution_data.get('active', False),
                priority=contribution_data.get('priority', 0),
            )

            seed_result = await samples_repo.create_translation_seed(seed)
            seed_id = seed_result.id

            sample = TranslationSampleCreate(
                seed_data_id=seed_id,
                language_id=language_id,
                translated_text=contribution_data['translated_text'],
                active=contribution_data.get('active', False),
                priority=contribution_data.get('priority', 0),
            )

            sample_result = await samples_repo.create_translation_sample(sample)
            sample_id = sample_result.id

            contribution_payload = ContributionCreate(
                target_text=contribution_data['translated_text'],
                language_id=language_id
            )

        elif contribution_type == "annotation":
            seed = AnnotationSeedCreate(
                image_url=contribution_data['image_url'],
                annotation_text=contribution_data['seed_text'],
                category=contribution_data.get('category'),
                active=False
            )
            seed_result = await samples_repo.create_annotation_seed(seed)
            seed_id = seed_result.id

            sample = AnnotationSampleCreate(
                seed_data_id=seed_id,
                language_id=language_id,
                active=False
            )

            sample_result = await samples_repo.create_annotation_sample(sample)

            sample_id = sample_result.id

            contribution_payload = ContributionCreate(
                target_text=contribution_data['annotation_text'],
                language_id=language_id
            )

        else:
            raise ValueError("Invalid contribution type")

        # Create the contribution using the standardized flow
        created_contribution = await self.create_contribution(
            user_id=user_id,
            contribution_type=contribution_type,
            sample_id=sample_id,
            data=contribution_payload,
            language_id=language_id,
            challenge_id=challenge_id
        )

        return {
            "type": contribution_type,
            "sample_id": sample_id,
            "seed_id": seed_id,
            "contribution_id": created_contribution.id
        }

    async def record_raw_contribution(self, event_id: str, user_id: str, contribution_type: str, metrics: dict):

        from services.challenge_service import ChallengeService
        challenge_service = ChallengeService(self.db)
        # Gets or creates participation
        participation = await challenge_service.get_challenge_participation(event_id, user_id)

        participation.contribution_count += 1

        # Update based on type
        if contribution_type == "speech":
            participation.total_hours_speech += metrics.get("hours", 0)
        elif contribution_type == "translation":
            participation.total_sentences_translated += metrics.get("sentences", 0)
        elif contribution_type == "text":
            participation.total_tokens_produced += metrics.get("tokens", 0)

        participation.updated_at = datetime.utcnow()
        self.db.add(participation)
        await self.db.commit()
        await self.db.refresh(participation)
        return participation

    async def record_contribution_evaluation(self, event_id: str, user_id: str, accepted: bool,
                                             points_awarded: int = 0):

        from services.challenge_service import ChallengeService
        challenge_service = ChallengeService(self.db)
        # Gets or creates participation
        participation = await challenge_service.get_challenge_participation(event_id, user_id)

        if not participation:
            return None

        if accepted:
            participation.accepted_contributions += 1

        participation.total_points += points_awarded

        # Update scores
        if participation.contribution_count > 0:
            participation.acceptance_rate = participation.accepted_contributions / participation.contribution_count
            participation.contribution_acceptance_score = participation.acceptance_rate

        participation.updated_at = datetime.utcnow()
        self.db.add(participation)
        await self.db.commit()
        await self.db.refresh(participation)
        return participation
