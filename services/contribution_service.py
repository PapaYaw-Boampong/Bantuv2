from pydantic import UUID4
from random import choice
from typing import Dict, List, Optional, Union, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
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
    AnnotationContributionRead,
    TranscriptionContributionRead,
    TranslationContributionRead
)

from schemas.sample_data import (
    TranscriptionSampleCreate,
    TranslationSampleCreate,
    AnnotationSampleCreate,
    AnnotationSeedCreate,
    TranslationSeedCreate
)

from schemas.language import UserLanguageStatsUpdate

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
            challenge_id: Optional[UUID4],
            user_id: UUID4,
            contribution_type: str,
            sample_id: UUID4,
            language_id: UUID4,
            data: ContributionCreate,
    ) -> Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]:
        """Create a new contribution of the specified type"""
        model_class = await self._get_model_class(contribution_type)
        # Common fields
        contribution_data = {
            "user_id": user_id,
            "sample_id": sample_id,
            "created_at": datetime.now(timezone.utc),
            "active": False,
            "flagged": False,
            "accepted": False,
            "ancestors": {
                str(user_id): [0, str(challenge_id)] if challenge_id else [0, False]
            }
        }

        # insert id if applicable 
        if data.id:
            contribution_data['id'] = data.id


        language_service = LanguageService(self.db)
        from services.challenge_service import ChallengeService
        challenge_service = ChallengeService(self.db)

        stats_data = ParticipationUpdate(
            is_contribution=True
        )

        if contribution_type == "annotation" or contribution_type == "transcription":
            if  data.file_name == "":
                raise ValueError("Contribution cannot be empty")
        if contribution_type == "transaltion": 
            if data.target_text == "":
                raise ValueError("Contribution cannot be empty")

        # Type-specific fields
        if contribution_type in {"annotation", "translation"}:
            contribution_data["target_text"] = data.target_text
            word_list = data.target_text.strip().lower().split()

            if contribution_type == "annotation":
                contribution_data["file_name"] = data.file_name
                token_count = len(word_list)
                stats_data.total_annotation_tokens = token_count

            elif contribution_type == "translation":
                contribution_data["sample_text"] = data.sample_text
                stats_data.total_sentences_translated = 1

        elif contribution_type == "transcription":
            contribution_data["sample_text"] = data.sample_text
            contribution_data["file_name"] = data.file_name
            stats_data.total_hours_speech = data.speech_length

        # Save Contribution
        contribution = model_class(**contribution_data)
        self.db.add(contribution)
        await self.db.commit()
        await self.db.refresh(contribution)

        # Record challenge-specific stats 
        if challenge_id:
            await challenge_service.update_participation_stats(
                event_id=challenge_id,
                user_id=user_id,
                stats_data=stats_data
            )

        user_stats_data = UserLanguageStatsUpdate(
            total_hours_speech=stats_data.total_hours_speech,
            total_sentences_translated=stats_data.total_sentences_translated,
            total_annotation_tokens=stats_data.total_annotation_tokens,
            is_contribution=stats_data.is_contribution,
            is_evaluation=stats_data.is_evaluation
        )

        # update global stats
        await language_service.user_language_stats_repository.update_stats(
            user_id=user_id,
            language_id=language_id,
            task_type=contribution_type,
            stats_data=user_stats_data
        )

        await self.update_ancestors(
            contribution_type=contribution_type,
            contribution_id=contribution.id,
            user_id=user_id,
            challenge_id=challenge_id
        )

        from services.sample_data_service import SampleDataService

        sample_service = SampleDataService(self.db)
        
        await sample_service.update_sample_with_contribution(
            sample_id=sample_id,
            sample_type=contribution_type,
        )

        return contribution # patch to return the asset name and the type

    # =========== Read Operations ==========
    async def get_contribution(
            self,
            contribution_id: UUID4,
            contribution_type: str,
            include_assets:bool = True
    ) -> Union[AnnotationContributionRead, TranscriptionContributionRead, TranslationContributionRead]:
        """Get a specific contribution by ID and type"""
        model_class = await self._get_model_class(contribution_type)

        stmt = select(model_class).where(model_class.id == contribution_id)
        result = await self.db.execute(stmt)
        contribution: Union[
            AnnotationContribution, TranscriptionContribution, TranslationContribution] = result.scalars().first()

        if not contribution:
            raise ValueError(f"{contribution_type.capitalize()} contribution with ID {contribution_id} not found")
        
        # Include signed Url for asset retrieval
        signed_url = None
        if (contribution_type == "annotation" or contribution_type == "transcription") and include_assets:
            from services.storage_service import StorageService
            storage_service = StorageService()
            signed_url = await storage_service.generate_download_url(contribution.file_name)
        
        # Convert to the correct Pydantic schema
        if contribution_type == "annotation":
            return AnnotationContributionRead(
                **contribution.model_dump(exclude={"file_name"}),
                signed_url=signed_url
            )
        elif contribution_type == "transcription":
            return TranscriptionContributionRead(
                **contribution.model_dump(exclude={"file_name"}),
                signed_url=signed_url
            )
        elif contribution_type == "translation":
            return TranslationContributionRead(
                **contribution.model_dump()
            )
        else:
            raise ValueError(f"Unsupported contribution type: {contribution_type}")

    async def get_contribution_ancestors(
            self,
            contribution_id: UUID4,
            contribution_type: str
    ) -> Dict[UUID4, int]:
        contribution = await self.get_contribution(contribution_id, contribution_type)
        ancestors = contribution.ancestors
        if not ancestors:
            return {}
        return ancestors

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

    async def update_contribution(
            self,
            contribution_id: UUID4,
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
            contribution_id: UUID4,
            contribution_type: str
    ) -> None:
        """Mark a contribution as passed validation"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.accepted = True
        await self.db.commit()

    async def flag_contribution(
            self, contribution_id: UUID4,
            contribution_type: str
    ) -> None:
        """Flag a contribution for review"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.flagged = True
        await self.db.commit()

    async def toggle_active_state(
            self, contribution_id: UUID4,
            contribution_type: str, active: bool
    ) -> None:
        """Toggle the active state of a contribution"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.active = active
        await self.db.commit()

    # =========== Delete Operations ==========

    async def delete_contribution(
            self, contribution_id: UUID4,
            contribution_type: str
    ) -> bool:
        """Delete a contribution (soft delete by setting active=False)"""
        contribution = await self.get_contribution(contribution_id, contribution_type)
        contribution.active = False
        await self.db.commit()
        return True

        # =========== Stats and Analysis ==========

    async def get_user_contribution_stats(
            self,
            user_id: Optional[UUID4] = None,
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
                base_query.where(model_class.accepted == True).subquery()
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
    async def update_ancestors(
            self,
            contribution_id: UUID4,
            contribution_type: str,
            user_id: UUID4,
            challenge_id: Optional[UUID4] = None
    ) -> Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]:
        """
        Award points to a user for their contribution (integration with Reward System)
        This is a placeholder for integration with your reward system
        """
        contribution = await self.get_contribution(contribution_id, contribution_type,include_assets = False)

        if challenge_id:
            in_challenge = True
        else:
            in_challenge = False

        contribution.ancestors[user_id] = [0, in_challenge]
        await self.db.commit()

        return contribution

    # =========== Custom Contribution Creation ==========

    async def create_custom_contribution(
            self,
            user_id: UUID4,
            language_id: UUID4,
            contribution_data: ContributionCreate,
            contribution_type: str,
            challenge_id: Optional[UUID4] = None
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
                transcription_text=contribution_data['transcription_text'],
                category=contribution_data.get('category', None),
                language_id=language_id,

            )
            sample = await samples_repo.create_transcription_sample(transcription_sample)
            sample_id = sample.id

            # Prepare payload
            contribution_payload = ContributionCreate(
                file_name=contribution_data['file_name'],  # or whichever audio to start with
                sample_text=contribution_data['transcription_text'],
                speech_length=contribution_data.get("speech_length", 0.0)
            )

        elif contribution_type == "translation":
            seed = TranslationSeedCreate(
                original_text=contribution_data['sample_text'],
                category=contribution_data.get('category', None),
                active=contribution_data.get('active', False),
                priority=contribution_data.get('priority', 0),
            )

            seed_result = await samples_repo.create_translation_seed(seed)
            seed_id = seed_result.id

            sample = TranslationSampleCreate(
                language_id=language_id,
                seed_id=seed_id,
            )

            sample_result = await samples_repo.create_translation_sample(sample)
            sample_id = sample_result.id

            contribution_payload = ContributionCreate(
                target_text=contribution_data['translated_text'],
                sample_text=contribution_data['sample_text'],
            )

        elif contribution_type == "annotation":
            seed = AnnotationSeedCreate(
                image_url=contribution_data['image_url'],
                annotation_text=contribution_data['seed_text'],
                category=contribution_data.get('category'),
            )
            seed_result = await samples_repo.create_annotation_seed(seed)
            seed_id = seed_result.id

            sample = AnnotationSampleCreate(
                seed_data_id=seed_id,
                eval=False,
                language_id=language_id,
            )

            sample_result = await samples_repo.create_annotation_sample(sample)

            sample_id = sample_result.id

            contribution_payload = ContributionCreate(
                target_text=contribution_data['target_text'],
                file_name=contribution_data['file_name'],
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

    async def unpackPoints(
            self,
            contribution_id: UUID4,
            language_id: UUID4,
            contribution_type: str,

    ) -> bool:
        contribution = await self.get_contribution(contribution_id, contribution_type)

        ancestors = contribution.ancestors

        if not contribution:
            raise ValueError(f"Contribution with ID {contribution_id} not found")

        # Define pipe depths based on contribution type
        pipe_depths = {
            "annotation": settings.ANNOTATION_PIPE_DEPTH,
            "transcription": settings.TRANSCRIPTION_PIPE_DEPTH,
            "translation": settings.TRANSLATION_PIPE_DEPTH
        }
        total_pipe_depth = pipe_depths.get(contribution_type, 3)

        # Calculate scores
        ancestor_count = len(ancestors)

        from services.challenge_service import ChallengeService
        from services.language_service import LanguageService

        challenge_service = ChallengeService(self.db)
        language_service = LanguageService(self.db)

        for i, ancestor_id in enumerate(ancestors):
            user_id = ancestor_id
            points_data = ancestors[ancestor_id]
            points = points_data[0]
            challenge_id = points_data[1] if points_data[1] != False else None

            is_contributor = (i == 0)  # First ancestor is the contributor


            if is_contributor:
                # Calculate contributor score
                acceptance_score = (ancestor_count - 1) / total_pipe_depth
            else:
                # Calculate evaluator score
                acceptance_score = points / (total_pipe_depth - 1) if total_pipe_depth > 1 else 1

            # Update challenge participation scores if this is part of a challenge
            if challenge_id:
                await challenge_service.update_challenge_participation_scores(
                    event_id=challenge_id,
                    user_id=UUID4(user_id),
                    is_contribution=is_contributor,
                    is_evaluation= not is_contributor,
                    acceptance_score=acceptance_score,
                    points=points
                )

            # Update global language stats scores regardless
            await language_service.user_language_stats_repository.update_user_language_scores(
                user_id=user_id,
                language_id=language_id,
                task_type=contribution_type,
                is_contribution=is_contributor,
                is_evaluation=not is_contributor,
                acceptance_score=acceptance_score
            )

        return True
