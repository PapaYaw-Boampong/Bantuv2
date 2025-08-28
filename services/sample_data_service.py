import uuid
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
from random import choice
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.inspection import inspect
from core.config import settings
from services.storage_service import StorageService
import random
import tempfile
import zipfile
import os
import time

from models import (
    AnnotationContribution,
    TranscriptionContribution,
    TranslationContribution,

    TranslationSeedData,
    AnnotationSeedData,

    AnnotationSample,
    TranscriptionSample,
    TranslationSample,
)
from schemas.sample_data import (
    TranscriptionSampleCreate,
    TranslationSeedCreate,
    TranslationSampleCreate,
    AnnotationSeedCreate,
    AnnotationSampleCreate,
    AnnotationSampleOut
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

        self.seed_types = {
            "annotation": AnnotationSeedData,
            "translation": TranslationSeedData
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

    # --- Core Sample Management ---

    async def get_seed_data(self, seed_id: uuid.UUID) -> Optional[TranslationSeedData]:
        """Fetch seed data by ID"""
        stmt = select(TranslationSeedData).where(TranslationSeedData.id == seed_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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
            include_seed_data: bool = False,
            user_id: Optional[uuid.UUID] = None,
            buffer: List[uuid.UUID] = []
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
                model.eval == active,
                model.priority >= priority_threshold,
                model.seed_count < max_instance_width,
            ]

        # Add language condition if provided
        if language_id:
            base_conditions.append(model.language_id == language_id)

        contribution_class = await self._get_model_class(contribution_type)

        user_contributed_subquery = (
            select(getattr(contribution_class, "sample_id"))
            .where(contribution_class.user_id == user_id)
            .subquery()
        )

        # Construct the query excluding samples the user has already contributed to
        query = select(model).where(and_(*base_conditions))
        query = query.where(model.id.not_in(select(user_contributed_subquery.c.sample_id)))
        query = query.where(model.id.not_in(buffer))

        # Select only IDs if requested
        if ids_only:
            query = select(model.id)

        # Conditionally preload seed data
        if include_seed_data and (not ids_only) and (contribution_type in self.seed_types):
            seed_model = self.seed_types[contribution_type]
            mapper = inspect(model)

            # Find the relationship key that matches the seed model
            for rel in mapper.relationships:
                if rel.mapper.class_ == seed_model:
                    query = query.options(selectinload(getattr(model, rel.key)))
                    break

        fetch_limit = limit * 3
        query = query.order_by(model.priority.desc()).limit(fetch_limit)

        result = await self.db.execute(query)

        if ids_only:
            # Get more samples than needed, then randomly select from them
            all_samples = [row[0] for row in result.fetchall()]
            import random
            random.shuffle(all_samples)  # Shuffle in place
            samples = all_samples[:limit]  # Take only what we need
        else:
            all_samples = list(result.scalars().all())
            import random
            random.shuffle(all_samples)  # Shuffle in place
            samples = all_samples[:limit]  # Take only what we need

        # If no samples found, and we have a language_id, try to create samples from available seeds
        if len(samples) == 0 and language_id and contribution_type in ["translation", "annotation"]:

            samples = await self.create_samples_from_seeds(
                contribution_type=contribution_type,
                language_id=language_id,
                limit=limit
            )

            if ids_only and samples:
                return [sample.id for sample in samples]
    
        result = samples
        
        return result

    async def create_samples_from_seeds(
            self,
            contribution_type: str,
            language_id: uuid.UUID,
            limit: int = 10
    ) -> List:
        """
        Create samples using available seeds for a specific language

        Args:
            contribution_type: The type of contribution ('translation' or 'annotation')
            language_id: The ID of the language to create samples for
            limit: Maximum number of samples to create

        Returns:
            List of newly created samples
        """
        if contribution_type not in ["translation", "annotation"]:
            return []

        if contribution_type not in self.seed_types:
            raise ValueError(f"No seed type defined for {contribution_type}")

        seed_model = self.seed_types[contribution_type]
        sample_model = self.sample_types[contribution_type]

        # Find seeds that are not already used for this language
        existing_samples_subquery = (
            select(getattr(sample_model, "seed_data_id"))
            .where(sample_model.language_id == language_id)
            .subquery()
        )

        # Query for available seeds
        seed_query = (
            select(seed_model)
            .where(seed_model.id.not_in(select(existing_samples_subquery.c.seed_data_id)))
            .where(seed_model.active == False)
            .order_by(func.random())
            .limit(settings.Replenish_SAMPLES_LIMIT)
        )

        seed_result = await self.db.execute(seed_query)
        seeds = list(seed_result.scalars().all())

        if not seeds:
            return []

        # Create samples from the available seeds
        new_samples = []
        for seed in seeds:
            if contribution_type == "translation":
                sample = TranslationSample(
                    seed_data_id=seed.id,
                    language_id=language_id,
                    eval=False,  # Not active until assigned
                    priority=5,  # Default medium priority
                    seed_count=0
                )
            elif contribution_type == "annotation":
                sample = AnnotationSample(
                    seed_data_id=seed.id,
                    language_id=language_id,
                    eval=False,  # Not active until assigned
                    priority=5,  # Default medium priority
                    seed_count=0,
                    file_name=seed.file_name
                )
            else:
                continue  # Skip if not a valid type

            self.db.add(sample)
            new_samples.append(sample)

        await self.db.commit()

        # Refresh all the samples to get their IDs and relationships
        for sample in new_samples:
            await self.db.refresh(sample)

        random.shuffle(new_samples)

        return new_samples[:limit]  # Return only the requested limit

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
            priority_threshold: int = 0,
            user_id: Optional[uuid.UUID] = None,
            currently_buffered: List[uuid.UUID] = []
    ) -> List[TranscriptionSample]:
        """Get transcription samples with priority-based selection"""
        return await self.get_samples(
            TranscriptionSample,
            "transcription",
            language_id,
            limit,
            priority_threshold,
            include_seed_data=True,
            user_id=user_id,
            buffer=currently_buffered
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
            priority_threshold: int = 0,
            user_id: Optional[uuid.UUID] = None,
            currently_buffered: List[uuid.UUID] = []

    ) -> List[TranslationSample]:
        """Get translation samples with priority-based selection"""
        return await self.get_samples(
            TranslationSample,
            "translation",
            language_id,
            limit,
            priority_threshold,
            include_seed_data=True,
            user_id=user_id,
            buffer= currently_buffered 
        )

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
            priority_threshold: int = 0,
            user_id: Optional[uuid.UUID] = None,
            currently_buffered: List[uuid.UUID] = []
    ) -> List[AnnotationSampleOut]:
        """Get annotation samples with priority-based selection"""
        orm_samples =  await self.get_samples(
            AnnotationSample,
            "annotation",
            language_id,
            limit,
            priority_threshold,
            include_seed_data=True,
            user_id=user_id,
            buffer=currently_buffered
        )

        storage = StorageService()

        output = []
        for sample in orm_samples:
            sample_out = AnnotationSampleOut.model_validate(sample)

            if sample_out.annotation_seed_data and sample_out.annotation_seed_data.file_name:
                try:
                    sample_out.annotation_seed_data.signed_url = storage.generate_download_url(
                        sample_out.annotation_seed_data.file_name
                    )
                except Exception:
                    sample_out.annotation_seed_data.signed_url = None

            output.append(sample_out)

        return output

    async def get_selected_seed_fields(
        self,
        seed_ids: Optional[List[uuid.UUID]] = None,
        fields: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Retrieve selected fields from AnnotationSeedData records.

        Args:
            seed_ids: List of seed UUIDs to filter by.
            fields: List of fields to include. Defaults to a safe subset.
            active_only: If True, filters only active seeds.

        Returns:
            A list of dictionaries with selected field values.
        """
        default_fields = ["id", "file_name", "annotation_text", "category"]
        selected_fields = fields or default_fields

        stmt = select(*[getattr(AnnotationSeedData, f) for f in selected_fields])

        stmt = stmt.where(AnnotationSeedData.id.in_(seed_ids))

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]



    # --- Sample Assignment & updates---
    async def assign_user_to_sample(
            self,
            language_id: uuid.UUID,
            user_id: uuid.UUID,
            sample_type: str,
            limit: int = 3,
            buffered_samples: List[uuid.UUID] = []
    ) -> List[Dict[str, Any]]:

        sample_ids = await self.find_samples_for_user(
            language_id=language_id,
            contribution_type=sample_type,
            user_id=user_id,
            limit=limit,
            evaluation_mode=False,
            active_samples= buffered_samples
            )

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

        return structured_samples

    async def find_samples_for_user(
            self,
            user_id: uuid.UUID,
            contribution_type: str,
            language_id: uuid.UUID,
            limit: int = 1,
            evaluation_mode: bool = False,
            active_samples: List[uuid.UUID] = []
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


        # Select a sample that hasn't been contributed to by this user and dont have existing instances
        query = (
            select(getattr(sample_class, "id"))
            .where(sample_class.id.not_in(select(user_contributed_subquery.c.sample_id)))
            
             .where(sample_class.id.not_in(active_samples))
             .where(sample_class.eval == evaluation_mode)
            .where(sample_class.language_id == language_id)
        )

        if evaluation_mode:
            query = query.where(sample_class.seed_count >= width)
            query = query.where(sample_class.evaluation_instance_id.is_not(None))
        
        else:
            query = query.where(sample_class.seed_count < width)
            query = query.where(sample_class.evaluation_instance_id.is_(None))

        result = await self.db.execute(query)
        samples = result.scalars().all()

        if not result:
            raise ValueError(f"No available {contribution_type} samples found for user")

        # Randomly select from available samples up to the limit
        selected_samples = [choice(samples) for _ in range(min(limit, len(samples)))]
        return selected_samples

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

        if sample.seed_count >= settings.EVAL_INSTANCE_WIDTH:
            sample.eval = True


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
            ).values(eval=state)
        elif sample_type == "translation":
            stmt = update(TranslationSample).where(
                TranslationSample.id.in_(sample_ids)
            ).values(eval=state)
        elif sample_type == "annotation":
            stmt = update(AnnotationSample).where(
                AnnotationSample.id.in_(sample_ids)
            ).values(eval=state)
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
    # keep pure, manually upload to gcp flicker 30k
    async def bulk_create_annotation_seeds_from_csv(
            self, csv_file: UploadFile, language_id: uuid.UUID
    ) -> int:
        df = read_csv_upload(csv_file)

        required_fields = ['image_url', 'seed_text']
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
                eval=row.get('eval', False)
            )
            self.db.add(sample)
            seeds.append(sample)

        await self.db.commit()
        return len(seeds)


    async def bulk_upload_annotation_seeds(
        self,
        captions_file: UploadFile,
        images_zip: UploadFile,
    ) -> dict:
        count = 0
        failed_uploads = []
        duplicate_files = set()
        seen_filenames = set()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # === Extract ZIP ===
            zip_path = os.path.join(tmp_dir, images_zip.filename)
            with open(zip_path, "wb") as f:
                f.write(await images_zip.read())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)

            # === Build lookup map for image filenames (case-insensitive, full tree) ===
            image_lookup = {}
            for root, _, files in os.walk(tmp_dir):
                for fname in files:
                    image_lookup[fname.strip().lower()] = os.path.join(root, fname)

            # === Parse CSV ===
            content = (await captions_file.read()).decode("utf-8")
            rows = content.strip().split("\n")

            for row in rows:
                if "\t" not in row:
                    continue

                try:
                    image_id_full, caption, source = row.strip().split("\t")
                    image_filename = image_id_full.split("#")[0]

                    if image_filename in seen_filenames:
                        duplicate_files.add(image_filename)
                        continue  # Avoid duplicate image names in one upload

                    seen_filenames.add(image_filename)

                    # Use lookup map
                    local_image_path = image_lookup.get(image_filename)

                    if not local_image_path or not os.path.exists(local_image_path):
                        failed_uploads.append({
                            "filename": image_filename,
                            "reason": "Image not found in ZIP"
                        })
                        continue

                    # === Upload Image ===
                    seed_id = str(uuid.uuid4())
                    timestamp = int(time.time())
                    gcs_path = f"contributions/annotation/{seed_id}/{timestamp}.jpg"

                    try:
                        storage = StorageService()
                        storage.upload_local_file(local_image_path, gcs_path)
                    except Exception as e:
                        failed_uploads.append({"filename": image_filename, "reason": f"GCS upload failed: {str(e)}"})
                        continue

                    # === Create DB Record ===
                    try:
                        sample = AnnotationSeedData(
                            id=seed_id,
                            file_name=gcs_path,
                            annotation_text=caption,
                            source=source
                        )

                        self.db.add(sample)
                        count += 1
                    except Exception as e:
                        failed_uploads.append({"filename": image_filename, "reason": f"DB error: {str(e)}"})
                        continue

                except ValueError:
                    failed_uploads.append({"filename": row, "reason": "Invalid row format (expected 3 columns)"})
                    continue

            await self.db.commit()

        return {
            "success": True,
            "inserted": count,
            "duplicates": list(duplicate_files),
            "failed": failed_uploads
        }


    async def bulk_create_transcription_seeds_from_csv(
            self, csv_file: UploadFile, language_id: uuid.UUID
    ) -> int:
        df = read_csv_upload(csv_file)

        required_fields = ['transcription_text']
        if not all(field in df.columns for field in required_fields):
            raise ValueError("CSV must include 'audio_urls' and 'transcription_text'.")

        seeds = []
        for _, row in df.iterrows():
            seed = TranscriptionSample(
                language_id=language_id,
                transcription_text=row['transcription_text'],
                category=row.get('category'),
                eval=row.get('eval', False)
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
