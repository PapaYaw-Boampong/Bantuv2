import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload

from core.config import settings
from models import (
    TranscriptionSample,
    TranslationSeedData,
    TranslationSample,
    AnnotationSeedData,
    AnnotationSample,
    Language
)
from schemas.sample_data import (
    TranscriptionSampleCreate,
    TranslationSeedCreate,
    TranslationSampleCreate,
    AnnotationSeedCreate,
    AnnotationSampleCreate
)

import pandas as pd
from io import StringIO
from fastapi import UploadFile


def read_csv_upload(file: UploadFile) -> pd.DataFrame:
    content = file.file.read().decode("utf-8")
    return pd.read_csv(StringIO(content))


class SampleDataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Core Sample Management ---

    async def get_samples(
            self,
            model,
            contribution_type: str,
            language_id: Optional[uuid.UUID] = None,
            limit: int = 10,
            priority_threshold: int = 0,
            active: bool = False,
            evaluate: bool = False,
            ids_only: bool = False,
    ) -> List:
        """Generic sample fetcher with optional ID-only mode and priority-based selection"""

        # Determine max contribution width for sample filtering
        if evaluate:
            base_conditions = [
                model.eval == evaluate,
                model.priority >= priority_threshold,
            ]
        else:
            max_instance_width = {
                "translation": settings.TRANSLATION_BASE_WIDTH,
                "annotation": settings.ANNOTATION_BASE_WIDTH,
                "transcription": settings.TRANSCRIPTION_BASE_WIDTH,
            }.get(contribution_type, settings.DEFAULT_BASE_WIDTH)

            base_conditions = [
                model.active == active,
                model.priority >= priority_threshold,
                model.store < max_instance_width,
            ]

        # Add language condition if provided
        if language_id:
            base_conditions.append(model.language_id == language_id)

        # Select only IDs if requested
        query = select(model.id if ids_only else model).where(and_(*base_conditions))
        query = query.order_by(model.priority.desc(), func.random()).limit(limit)

        result = await self.db.execute(query)

        if ids_only:
            return [row[0] for row in result.fetchall()]
        return list(result.scalars().all())

    async def create_transcription_sample(
            self,
            sample_data: TranscriptionSampleCreate
    ) -> TranscriptionSample:
        """Create a new transcription sample"""
        sample = TranscriptionSample(**sample_data.model_dump())
        self.db.add(sample)
        await self.db.commit()
        await self.db.refresh(sample)
        return sample

    async def get_transcription_samples(
            self,
            language_id: Optional[uuid.UUID] = None,
            limit: int = 10,
            priority_threshold: int = 0
    ) -> List[TranscriptionSample]:
        """Get transcription samples with priority-based selection"""
        return await self.get_samples(
            TranscriptionSample,
            "transcription",
            language_id,
            limit,
            priority_threshold
        )

    # --- Translation Samples ---

    async def create_translation_seed(
            self,
            seed_data: TranslationSeedCreate
    ) -> TranslationSeedData:
        """Create new translation seed data"""
        seed = TranslationSeedData(**seed_data.model_dump())
        self.db.add(seed)
        await self.db.commit()
        await self.db.refresh(seed)
        return seed

    async def create_translation_sample(
            self,
            sample_data: TranslationSampleCreate
    ) -> TranslationSample:
        """Create a new translation sample"""
        sample = TranslationSample(**sample_data.model_dump())
        self.db.add(sample)
        await self.db.commit()
        await self.db.refresh(sample)
        return sample

    async def get_translation_samples(
            self,
            language_id: Optional[uuid.UUID] = None,
            limit: int = 10,
            priority_threshold: int = 0
    ) -> List[TranslationSample]:
        """Get translation samples with priority-based selection"""
        return await self.get_samples(
            TranslationSample,
            "translation",
            language_id,
            limit,
            priority_threshold
        )

    # async def get_sample_word_frequencies(
    #         self,
    #         sample_id: uuid.UUID,
    #         sample_type: str,
    # ) -> Dict[str, int]:
    #     """Get word frequencies for a specific sample"""
    #     sample_model = {
    #         "translation": TranslationSample,
    #         "annotation": AnnotationSample,
    #         "transcription": TranscriptionSample
    #     }.get(sample_type)
    #
    #     stmt = select(sample_model).where(
    #         TranslationSample.id == sample_id,
    #     )
    #
    #     result = await self.db.execute(stmt)
    #     sample = result.scalar_one_or_none()
    #
    #     if not sample or not sample.words:
    #         return {}
    #
    #     return sample.words

    # --- Annotation Samples ---

    async def create_annotation_seed(
            self,
            seed_data: AnnotationSeedCreate
    ) -> AnnotationSeedData:
        """Create new annotation seed data"""
        seed = AnnotationSeedData(**seed_data.model_dump())
        self.db.add(seed)
        await self.db.commit()
        await self.db.refresh(seed)
        return seed

    async def create_annotation_sample(
            self,
            sample_data: AnnotationSampleCreate
    ) -> AnnotationSample:
        """Create a new annotation sample"""
        sample = AnnotationSample(**sample_data.model_dump())
        self.db.add(sample)
        await self.db.commit()
        await self.db.refresh(sample)
        return sample

    async def get_annotation_samples(
            self,
            language_id: Optional[uuid.UUID] = None,
            limit: int = 10,
            priority_threshold: int = 0
    ) -> List[AnnotationSample]:
        """Get annotation samples with priority-based selection"""
        return await self.get_samples(
            AnnotationSample,
            "annotation",
            language_id,
            limit,
            priority_threshold
        )

    # --- Sample Assignment & updates---
    async def assign_user_to_sample(
            self,
            language_id: uuid.UUID,
            user_id: uuid.UUID,
            sample_type: str,
            limit: int = 3
    ) -> List[Dict[str, Any]]:
        from services.contribution_service import ContributionManagementService
        contributions = ContributionManagementService(self.db)

        sample_ids = await contributions.find_samples_for_user(language_id, sample_type, user_id, limit)

        if not sample_ids:
            return []

        if sample_type == "transcription":
            stmt = select(TranscriptionSample).where(
                TranscriptionSample.id.in_(sample_ids)
            )
        elif sample_type == "translation":
            stmt = select(TranslationSample).where(
                TranslationSample.id.in_(sample_ids)
            )
        elif sample_type == "annotation":
            stmt = select(AnnotationSample).options(
                selectinload(AnnotationSample.annotation_seed_data)
            ).where(
                AnnotationSample.id.in_(sample_ids)
            )
        else:
            raise ValueError(f"Unsupported sample type: {sample_type}")

        result = await self.db.execute(stmt)
        samples = result.scalars().all()

        structured_samples = [{"TTE": settings.TTE}]
        for sample in samples:
            if sample_type == "transcription":
                structured_samples.append({
                    "id": str(sample.id),
                    "language_id": str(sample.language_id),
                    "text": sample.transcription_text,
                    "category": sample.category,
                    "sample_type": "transcription"
                })

            elif sample_type == "translation":
                structured_samples.append({
                    "id": str(sample.id),
                    "language_id": str(sample.language_id),
                    "source_text": sample.source_text,
                    "target_text": sample.translation_text,
                    "category": sample.category,
                    "sample_type": "translation"

                })

            elif sample_type == "annotation":
                seed = sample.annotation_seed_data
                structured_samples.append({
                    "id": str(sample.id),
                    "language_id": str(sample.language_id),
                    "seed_id": str(seed.id),
                    "image_url": seed.image_url,
                    "annotation_text": seed.annotation_text,
                    "category": seed.category,
                    "sample_type": "annotation"
                })

        await self.lock_samples(sample_ids, sample_type)

        return structured_samples

    async def update_sample_with_contribution(
            self,
            sample_id: uuid.UUID,
            sample_type: str,
    ):
        # Select the appropriate model
        sample_model = {
            "translation": TranslationSample,
            "annotation": AnnotationSample,
            "transcription": TranscriptionSample
        }.get(sample_type)

        if not sample_model:
            raise ValueError(f"Unsupported sample type: {sample_type}")

        # Get the sample
        stmt = select(sample_model).where(sample_model.id == sample_id)
        result = await self.db.execute(stmt)
        sample = result.scalar_one_or_none()

        if not sample:
            raise ValueError("Sample not found")

        sample.seed_count += 1

        self.db.add(sample)
        await self.db.commit()
        await self.db.refresh(sample)

        return sample

    async def lock_samples(
            self,
            sample_ids: List[uuid.UUID],
            sample_type: str,
            state: bool
    ) -> None:
        if sample_type == "transcription":
            stmt = update(TranscriptionSample).where(
                TranscriptionSample.id.in_(sample_ids)
            ).values(active=state)
        elif sample_type == "translation":
            stmt = update(TranslationSample).where(
                TranslationSample.id.in_(sample_ids)
            ).values(active=state)
        elif sample_type == "annotation":
            stmt = update(AnnotationSample).where(
                AnnotationSample.id.in_(sample_ids)
            ).values(active=state)
        else:
            raise ValueError(f"Unsupported sample type: {sample_type}")

        await self.db.execute(stmt)
        await self.db.commit()

    # --- Bulk Operations ---

    async def bulk_create_transcription_samples(
            self,
            samples: List[TranscriptionSampleCreate]
    ) -> int:
        """Bulk create transcription samples"""
        count = 0
        for sample_data in samples:
            sample = TranscriptionSample(**sample_data.model_dump())
            self.db.add(sample)
            count += 1
        await self.db.commit()
        return count

    async def bulk_create_translation_pairs(
            self,
            seed_data: TranslationSeedCreate,
            translations: List[TranslationSampleCreate]
    ) -> int:
        """Create seed + multiple translations atomically"""
        seed = await self.create_translation_seed(seed_data)
        count = 0
        for trans_data in translations:
            trans_data.seed_data_id = seed.id
            await self.create_translation_sample(trans_data)
            count += 1
        return count

    # --- Priority Management ---

    async def update_sample_priority(
            self,
            sample_id: uuid.UUID,
            model_type: str,  # 'transcription', 'translation', or 'annotation'
            priority: int
    ) -> bool:
        """Update priority of any sample type"""
        models = {
            'transcription': TranscriptionSample,
            'translation': TranslationSample,
            'annotation': AnnotationSample
        }

        model = models.get(model_type.lower())
        if not model:
            raise ValueError("Invalid model type")

        result = await self.db.execute(
            select(model).where(model.id == sample_id)
        )
        sample = result.scalar_one_or_none()

        if sample:
            sample.priority = priority
            await self.db.commit()
            return True
        return False

    # --- Custom Contributions ---

    # csv enabled functions

    async def bulk_create_annotation_seeds_from_csv(
            self, csv_file: UploadFile, language_id: uuid.UUID
    ) -> int:
        df = read_csv_upload(csv_file)

        required_fields = ['image_url', 'seed_text', 'annotations']
        if not all(field in df.columns for field in required_fields):
            raise ValueError("CSV must include 'image_url', 'seed_text', and 'annotations'.")

        seeds = []
        for _, row in df.iterrows():
            seed_data = AnnotationSeedData(
                image_url=row['image_url'],
                annotation_text=row['seed_text'],
                category=row.get('category'),
                active=row.get('active', False)
            )
            self.db.add(seed_data)
            await self.db.commit()

            sample = AnnotationSample(
                seed_data_id=seed_data.id,
                language_id=language_id,
                annotation_result=row['annotations'],
                active=row.get('active', False)
            )
            self.db.add(sample)
            seeds.append(sample)

        await self.db.commit()
        return len(seeds)

    async def bulk_create_transcription_seeds_from_csv(
            self, csv_file: UploadFile, language_id: uuid.UUID
    ) -> int:
        df = read_csv_upload(csv_file)

        required_fields = ['audio_urls', 'transcription_text']
        if not all(field in df.columns for field in required_fields):
            raise ValueError("CSV must include 'audio_urls' and 'transcription_text'.")

        seeds = []
        for _, row in df.iterrows():
            seed = TranscriptionSample(
                language_id=language_id,
                audio_urls=row['audio_urls'],  # Expecting comma-separated string
                transcription_text=row['transcription_text'],
                category=row.get('category'),
                active=row.get('active', False)
            )
            self.db.add(seed)
            seeds.append(seed)

        await self.db.commit()
        return len(seeds)

    async def bulk_create_translation_seeds_from_csv(
            self, csv_file: UploadFile
    ) -> int:
        df = read_csv_upload(csv_file)

        if "original_text" not in df.columns:
            raise ValueError("CSV must include 'original_text' column.")

        seeds = []
        for _, row in df.iterrows():
            seed = TranslationSeedData(
                original_text=row['original_text'],
                category=row.get('category'),
                active=row.get('active', True)
            )
            self.db.add(seed)
            seeds.append(seed)

        await self.db.commit()
        return len(seeds)
