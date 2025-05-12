import uuid
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from crud.language import LanguageCrud, UserLanguageCrud, UserLanguageStatsCrud
from pydantic import UUID4
from datetime import datetime, timedelta
from sqlalchemy import select, func, text

from models.challenge import Challenge, ChallengeStatus, TaskType
from models.contribution import (
    TranslationContribution,
    AnnotationContribution,
    TranscriptionContribution
)
from models.data_store import (
    TranslationSample,
    AnnotationSample,
    TranscriptionSample
)


class StatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.language_repository = LanguageCrud(db)
        self.user_language_repository = UserLanguageCrud(db)
        self.user_language_stats_repository = UserLanguageStatsCrud(db)

    async def get_language_stats(self, language_id: str) -> dict:
        """
        Get comprehensive language statistics for analytics dashboards

        Args:
            language_id: The ID of the language to get stats for

        Returns:
            Dictionary containing various language statistics
        """
        try:
            lang_uuid = UUID4(language_id)
        except ValueError:
            # Try to find by code if not a valid UUID
            language = await self.language_repository.get_by_code(language_id)
            if not language:
                language = await self.language_repository.get_by_name(language_id)
                if not language:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Language with ID/code '{language_id}' not found"
                    )
            lang_uuid = language.id

        # Get the language
        language = await self.language_repository.get_by_id(lang_uuid)
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Language with ID '{language_id}' not found"
            )

        # Base stats from language model
        stats = {
            "id": str(language.id),
            "name": language.name,
            "code": language.code,
            "total_contributors": language.contributor_count,
            "total_contributions": language.contribution_count,
        }

        # Get challenges stats
        challenges_query = select(Challenge).where(
            Challenge.language_id == lang_uuid,
            Challenge.status.in_([ChallengeStatus.ACTIVE, ChallengeStatus.UPCOMING])
        )
        result = await self.db.execute(challenges_query)
        challenges = list(result.scalars().all())

        active_challenges = [c for c in challenges if c.status == ChallengeStatus.ACTIVE]
        upcoming_challenges = [c for c in challenges if c.status == ChallengeStatus.UPCOMING]

        stats["challenges"] = {
            "active_count": len(active_challenges),
            "upcoming_count": len(upcoming_challenges),
            "total_participants": sum(c.participant_count for c in challenges),
            "by_type": {}
        }

        # Count challenges by task type
        for task_type in TaskType:
            task_challenges = [c for c in challenges if c.task_type == task_type]
            stats["challenges"]["by_type"][task_type.value] = len(task_challenges)

        # Flagged contributions
        translation_flagged = await self.db.execute(
            select(func.count(TranslationContribution.id))
            .where(TranslationContribution.flagged == True)
            .join(TranslationSample)
            .where(TranslationSample.language_id == lang_uuid)
        )
        annotation_flagged = await self.db.execute(
            select(func.count(AnnotationContribution.id))
            .where(AnnotationContribution.flagged == True)
            .join(AnnotationSample)
            .where(AnnotationSample.language_id == lang_uuid)
        )
        transcription_flagged = await self.db.execute(
            select(func.count(TranscriptionContribution.id))
            .where(TranscriptionContribution.flagged == True)
            .join(TranscriptionSample)
            .where(TranscriptionSample.language_id == lang_uuid)
        )

        stats["flagged_contributions"] = {
            "translation": translation_flagged.scalar() or 0,
            "annotation": annotation_flagged.scalar() or 0,
            "transcription": transcription_flagged.scalar() or 0,
            "total": (translation_flagged.scalar() or 0) +
                     (annotation_flagged.scalar() or 0) +
                     (transcription_flagged.scalar() or 0)
        }

        # Active users in the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Get unique users who contributed to this language in the last 30 days
        translation_users = await self.db.execute(
            select(func.count(func.distinct(TranslationContribution.user_id)))
            .join(TranslationSample)
            .where(
                TranslationSample.language_id == lang_uuid,
                TranslationContribution.created_at >= thirty_days_ago
            )
        )

        annotation_users = await self.db.execute(
            select(func.count(func.distinct(AnnotationContribution.user_id)))
            .join(AnnotationSample)
            .where(
                AnnotationSample.language_id == lang_uuid,
                AnnotationContribution.created_at >= thirty_days_ago
            )
        )

        transcription_users = await self.db.execute(
            select(func.count(func.distinct(TranscriptionContribution.user_id)))
            .join(TranscriptionSample)
            .where(
                TranscriptionSample.language_id == lang_uuid,
                TranscriptionContribution.created_at >= thirty_days_ago
            )
        )

        # Count contribution types
        translation_count = await self.db.execute(
            select(func.count(TranslationContribution.id))
            .join(TranslationSample)
            .where(TranslationSample.language_id == lang_uuid)
        )

        annotation_count = await self.db.execute(
            select(func.count(AnnotationContribution.id))
            .join(AnnotationSample)
            .where(AnnotationSample.language_id == lang_uuid)
        )

        transcription_count = await self.db.execute(
            select(func.count(TranscriptionContribution.id))
            .join(TranscriptionSample)
            .where(TranscriptionSample.language_id == lang_uuid)
        )

        # Calculate totals for pie chart percentages
        total_contributions = (
                (translation_count.scalar() or 0) +
                (annotation_count.scalar() or 0) +
                (transcription_count.scalar() or 0)
        )

        stats["active_users"] = {
            "translation": translation_users.scalar() or 0,
            "annotation": annotation_users.scalar() or 0,
            "transcription": transcription_users.scalar() or 0,
            "total_unique": await self._count_unique_users_across_types(lang_uuid, thirty_days_ago)
        }

        stats["contribution_distribution"] = {
            "translation": {
                "count": translation_count.scalar() or 0,
                "percentage": round(((translation_count.scalar() or 0) / max(total_contributions, 1)) * 100, 2)
            },
            "annotation": {
                "count": annotation_count.scalar() or 0,
                "percentage": round(((annotation_count.scalar() or 0) / max(total_contributions, 1)) * 100, 2)
            },
            "transcription": {
                "count": transcription_count.scalar() or 0,
                "percentage": round(((transcription_count.scalar() or 0) / max(total_contributions, 1)) * 100, 2)
            },
            "total": total_contributions
        }

        # Get accepted vs. rejected contributions ratio
        translation_accepted = await self._get_accepted_contributions_count("translation", lang_uuid)
        annotation_accepted = await self._get_accepted_contributions_count("annotation", lang_uuid)
        transcription_accepted = await self._get_accepted_contributions_count("transcription", lang_uuid)

        stats["acceptance_rates"] = {
            "translation": self._calculate_acceptance_rate(
                translation_accepted,
                (translation_count.scalar() or 0)
            ),
            "annotation": self._calculate_acceptance_rate(
                annotation_accepted,
                (annotation_count.scalar() or 0)
            ),
            "transcription": self._calculate_acceptance_rate(
                transcription_accepted,
                (transcription_count.scalar() or 0)
            ),
            "overall": self._calculate_acceptance_rate(
                translation_accepted + annotation_accepted + transcription_accepted,
                total_contributions
            )
        }

        # Add historic data (last 6 months)
        stats["monthly_activity"] = await self._get_monthly_activity(lang_uuid)

        return stats

    async def _count_unique_users_across_types(self, language_id: UUID4, since_date: datetime) -> int:
        """Count unique users across all contribution types"""
        query = """
        SELECT COUNT(DISTINCT user_id) FROM (
            SELECT tc.user_id 
            FROM translation_contribution tc
            JOIN translation_sample ts ON tc.sample_id = ts.id
            WHERE ts.language_id = :lang_id AND tc.created_at >= :since_date

            UNION

            SELECT ac.user_id 
            FROM annotation_contribution ac
            JOIN annotation_sample "as" ON ac.sample_id = "as".id
            WHERE "as".language_id = :lang_id AND ac.created_at >= :since_date

            UNION

            SELECT trc.user_id 
            FROM transcription_contribution trc
            JOIN transcription_sample trs ON trc.sample_id = trs.id
            WHERE trs.language_id = :lang_id AND trc.created_at >= :since_date
        ) AS unique_users
        """
        result = await self.db.execute(
            text(query),
            {"lang_id": language_id, "since_date": since_date}
        )
        return result.scalar() or 0

    async def _get_accepted_contributions_count(self, contribution_type: str, language_id: UUID4) -> int:
        """Get count of accepted contributions by type"""
        if contribution_type == "translation":
            query = select(func.count(TranslationContribution.id)) \
                .join(TranslationSample) \
                .where(
                TranslationSample.language_id == language_id,
                TranslationContribution.accepted == True
            )
        elif contribution_type == "annotation":
            query = select(func.count(AnnotationContribution.id)) \
                .join(AnnotationSample) \
                .where(
                AnnotationSample.language_id == language_id,
                AnnotationContribution.accepted == True
            )
        elif contribution_type == "transcription":
            query = select(func.count(TranscriptionContribution.id)) \
                .join(TranscriptionSample) \
                .where(
                TranscriptionSample.language_id == language_id,
                TranscriptionContribution.accepted == True
            )
        else:
            return 0

        result = await self.db.execute(query)
        return result.scalar() or 0

    def _calculate_acceptance_rate(self, accepted: int, total: int) -> dict:
        """Calculate acceptance rate and return percentage with count"""
        if total == 0:
            return {"percentage": 0, "accepted": 0, "total": 0}

        return {
            "percentage": round((accepted / total) * 100, 2),
            "accepted": accepted,
            "total": total
        }

    async def _get_monthly_activity(self, language_id: UUID4) -> dict:
        """Get monthly activity data for the past 6 months"""
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        # Use raw SQL for more complex time-based aggregation
        query = """
        SELECT 
            DATE_TRUNC('month', created_at) AS month,
            COUNT(*) as contribution_count,
            COUNT(DISTINCT user_id) as user_count
        FROM (
            SELECT tc.created_at, tc.user_id
            FROM translation_contribution tc
            JOIN translation_sample ts ON tc.sample_id = ts.id
            WHERE ts.language_id = :lang_id AND tc.created_at >= :since_date

            UNION ALL

            SELECT ac.created_at, ac.user_id
            FROM annotation_contribution ac
            JOIN annotation_sample "as" ON ac.sample_id = "as".id
            WHERE "as".language_id = :lang_id AND ac.created_at >= :since_date

            UNION ALL

            SELECT trc.created_at, trc.user_id
            FROM transcription_contribution trc
            JOIN transcription_sample trs ON trc.sample_id = trs.id
            WHERE trs.language_id = :lang_id AND trc.created_at >= :since_date
        ) AS all_contributions
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month
        """

        result = await self.db.execute(
            text(query),
            {"lang_id": language_id, "since_date": six_months_ago}
        )

        monthly_data = {}
        for row in result:
            month_str = row.month.strftime("%Y-%m")
            monthly_data[month_str] = {
                "contributions": row.contribution_count,
                "unique_users": row.user_count
            }

        return monthly_data
