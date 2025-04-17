from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from crud.language import UserLanguageCrud
from models.user import UserLanguage


class StatsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_language_repository = UserLanguageCrud(db)

    async def update_lang_speech_hours(
            self, user_id: str, language_id: str, hours: float, task_type: str
    ) -> UserLanguage:
        """
        Update the total speech hours for a user in a specific language.
        """
        return await self.user_language_repository.update_speech_hours(
            user_id, language_id, hours, task_type
        )

    async def update_lang_sentences_translated(
            self, user_id: str, language_id: str, sentences: int, task_type: str
    ) -> UserLanguage:
        """
        Update the total number of sentences translated for a user in a specific language.
        """
        return await self.user_language_repository.update_sentences_translated(
            user_id, language_id, sentences, task_type
        )

    async def update_lang_tokens_annotated(
            self, user_id: str, language_id: str, tokens: int, task_type: str
    ) -> UserLanguage:
        """
        Update the total number of tokens annotated for a user in a specific language.
        """
        return await self.user_language_repository.update_annotation_tokens(
            user_id, language_id, tokens, task_type
        )

    async def update_user_stats(
            self,
            user_id: str,
            language_id: str,
            task_type: str,
            challenge_id: Optional[str] = None,
            metrics: Optional[dict] = None,
            is_evaluation: bool = False,
            accepted: bool = True,
    ) -> None:
        """
        Update user stats either globally (UserLanguage) or within a challenge (ChallengeParticipation).

        Args:
            user_id: UUID as string
            language_id: UUID as string
            task_type: 'transcription' | 'translation' | 'annotation'
            challenge_id: Optional challenge UUID as string
            metrics: Dict with optional keys 'hours', 'sentences', 'tokens'
            is_evaluation: Whether the action is an evaluation
            accepted: Whether the contribution/evaluation was accepted
        """
        from services.challenge_service import ChallengeService
        cs = ChallengeService(self.db)

        if metrics is None:
            metrics = {}

        if challenge_id:
            await challenge_repupdate_participant_stats(
                user_id=user_id,
                challenge_id=challenge_id,
                task_type=task_type,
                is_evaluation=is_evaluation,
                accepted=accepted,
                metrics=metrics,
            )

        await self.user_language_repository.update_global_user_stats(
            user_id=user_id,
            language_id=language_id,
            task_type=task_type,
            is_evaluation=is_evaluation,
            accepted=accepted,
            metrics=metrics,
        )
