from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from database import get_session
from models.user import User
from schemas.sample_data import (
    TranscriptionSampleCreate,
    TranslationSeedCreate,
    TranslationSampleCreate,
    AnnotationSeedCreate,
    AnnotationSampleCreate,
    BulkTranscriptionSampleUpload,
    TranslationPairUpload,
    SampleLockUpdate,
    SamplePriorityUpdate
)
from services.sample_data_service import SampleDataService
from api.v1.deps import get_current_active_user, get_current_superuser
from core.config import settings

router = APIRouter()


# Dependencies
def get_sample_service(db: AsyncSession = Depends(get_session)):
    return SampleDataService(db)


# ======== TRANSCRIPTION SAMPLES ========

@router.post("/transcription/", summary="Create a transcription sample")
async def create_transcription_sample(
        sample: TranscriptionSampleCreate,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a new transcription sample"""
    try:
        return await service.create_transcription_sample(sample)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transcription/bulk", summary="Create multiple transcription samples")
async def bulk_create_transcription_samples(
        data: BulkTranscriptionSampleUpload,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create multiple transcription samples in a single request"""
    try:
        count = await service.bulk_create_transcription_samples(data.samples)
        return {"success": True, "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transcription/csv", summary="Create transcription samples from CSV")
async def bulk_create_transcription_from_csv(
        language_id: UUID,
        file: UploadFile = File(...),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Import transcription samples from a CSV file"""
    try:
        count = await service.bulk_create_transcription_seeds_from_csv(file, language_id)
        return {"success": True, "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transcription/", summary="Get transcription samples")
async def get_transcription_samples(
        language_id: Optional[UUID] = None,
        limit: int = Query(10, ge=1, le=100),
        priority_threshold: int = Query(0, ge=0),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get transcription samples with optional filtering"""
    try:
        samples = await service.get_transcription_samples(
            language_id=language_id,
            limit=limit,
            priority_threshold=priority_threshold
        )
        return {"samples": samples, "count": len(samples)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======== TRANSLATION SAMPLES ========

@router.post("/translation/seed", summary="Create a translation seed")
async def create_translation_seed(
        seed: TranslationSeedCreate,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a new translation seed"""
    try:
        return await service.create_translation_seed(seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/translation/", summary="Create a translation sample")
async def create_translation_sample(
        sample: TranslationSampleCreate,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a new translation sample"""
    try:
        return await service.create_translation_sample(sample)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/translation/pair", summary="Create a translation seed with samples")
async def create_translation_pair(
        data: TranslationPairUpload,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a translation seed and its corresponding samples in one request"""
    try:
        count = await service.bulk_create_translation_pairs(data.seed, data.translations)
        return {"success": True, "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/translation/csv", summary="Create translation seeds from CSV")
async def bulk_create_translation_from_csv(
        file: UploadFile = File(...),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Import translation seeds from a CSV file"""
    try:
        count = await service.bulk_create_translation_seeds_from_csv(file)
        return {"success": True, "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/translation/", summary="Get translation samples")
async def get_translation_samples(
        language_id: Optional[UUID] = None,
        limit: int = Query(10, ge=1, le=100),
        priority_threshold: int = Query(0, ge=0),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get translation samples with optional filtering"""
    try:
        samples = await service.get_translation_samples(
            language_id=language_id,
            limit=limit,
            priority_threshold=priority_threshold
        )
        return {"samples": samples, "count": len(samples)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======== ANNOTATION SAMPLES ========

@router.post("/annotation/seed", summary="Create an annotation seed")
async def create_annotation_seed(
        seed: AnnotationSeedCreate,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a new annotation seed"""
    try:
        return await service.create_annotation_seed(seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/annotation/", summary="Create an annotation sample")
async def create_annotation_sample(
        sample: AnnotationSampleCreate,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Create a new annotation sample"""
    try:
        return await service.create_annotation_sample(sample)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/annotation/csv", summary="Create annotation samples from CSV")
async def bulk_create_annotation_from_csv(
        language_id: UUID,
        file: UploadFile = File(...),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Import annotation seeds and samples from a CSV file"""
    try:
        count = await service.bulk_create_annotation_seeds_from_csv(file, language_id)
        return {"success": True, "count": count}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/annotation/", summary="Get annotation samples")
async def get_annotation_samples(
        language_id: Optional[UUID] = None,
        limit: int = Query(10, ge=1, le=100),
        priority_threshold: int = Query(0, ge=0),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_active_user)
):
    """Get annotation samples with optional filtering"""
    try:
        samples = await service.get_annotation_samples(
            language_id=language_id,
            limit=limit,
            priority_threshold=priority_threshold
        )
        return {"samples": samples, "count": len(samples)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======== SAMPLE ASSIGNMENT ========

@router.get("/assign/{sample_type}", summary="Assign samples to a user")
async def assign_samples_to_user(
        language_id: UUID = Query(..., description="ID of the language"),
        sample_type: str = Path(..., description="Type of sample (transcription, translation, annotation)"),
        limit: int = Query(3, ge=1, le=10, description="Number of samples to assign"),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_active_user)
):
    """Assign samples to the current user for contribution"""
    try:
        samples = await service.assign_user_to_sample(
            language_id=language_id,
            user_id=current_user.id,
            sample_type=sample_type,
            limit=limit
        )
        if not samples:
            raise HTTPException(status_code=404, detail=f"No available {sample_type} samples found")
        return samples
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ======== SAMPLE MANAGEMENT ========

@router.patch("/{sample_type}/{sample_id}/priority", summary="Update sample priority")
async def update_sample_priority(
        sample_id: UUID = Path(..., description="ID of the sample"),
        sample_type: str = Path(..., description="Type of sample (transcription, translation, annotation)"),
        data: SamplePriorityUpdate = None,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Update the priority of a sample"""
    if not data:
        raise HTTPException(status_code=400, detail="Priority data is required")

    try:
        result = await service.update_sample_priority(
            sample_id=sample_id,
            model_type=sample_type,
            priority=data.priority
        )
        if result:
            return {"message": f"{sample_type.capitalize()} sample priority updated successfully"}
        raise HTTPException(status_code=404, detail=f"{sample_type.capitalize()} sample not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{sample_type}/lock", summary="Lock or unlock samples")
async def lock_samples(
        sample_type: str = Path(..., description="Type of sample (transcription, translation, annotation)"),
        data: SampleLockUpdate = None,
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Lock or unlock multiple samples"""
    if not data:
        raise HTTPException(status_code=400, detail="Sample IDs and state are required")

    try:
        await service.lock_samples(
            sample_ids=data.sample_ids,
            sample_type=sample_type,
            state=data.state
        )
        state_str = "locked" if data.state else "unlocked"
        return {
            "message": f"{len(data.sample_ids)} {sample_type} samples {state_str} successfully",
            "affected_samples": [str(id) for id in data.sample_ids]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{sample_type}/{sample_id}/contribution-count", summary="Update sample contribution count")
async def update_sample_contribution_count(
        sample_id: UUID = Path(..., description="ID of the sample"),
        sample_type: str = Path(..., description="Type of sample (transcription, translation, annotation)"),
        service: SampleDataService = Depends(get_sample_service),
        current_user: User = Depends(get_current_superuser)
):
    """Increment the contribution count for a sample"""
    try:
        sample = await service.update_sample_with_contribution(
            sample_id=sample_id,
            sample_type=sample_type
        )
        return {
            "sample_id": str(sample.id),
            "contribution_count": sample.seed_count,
            "message": f"{sample_type.capitalize()} sample contribution count updated"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))