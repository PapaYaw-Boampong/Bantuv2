# backend/routes/storage.py
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone
from services.storage_service import StorageService

from schemas.storage import (
    UploadUrlRequest, 
    DownloadUrlRequest, 
    SignedUrlResponse
)

from api.v1.deps import get_current_active_user  # Your existing auth dependency

router = APIRouter()

# Dependency to get storage service
def get_storage_service() -> StorageService:
    return StorageService()

@router.post("/upload-url", response_model=SignedUrlResponse)
async def generate_upload_url(
    request: UploadUrlRequest,
    current_user = Depends(get_current_active_user),  # Ensure user is authenticated
    storage_service: StorageService = Depends(get_storage_service)
):
    """Generate a signed URL for uploading a file."""
    try:
        signed_url = storage_service.generate_upload_url(
            filename=request.filename,
            content_type=request.content_type
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat() + "Z"
        
        return SignedUrlResponse(
            signed_url=signed_url,
            expires_at=expires_at,
            filename=request.filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate upload URL: {str(e)}"
        )

@router.post("/download-url", response_model=SignedUrlResponse)
async def generate_download_url(
    request: DownloadUrlRequest,
    current_user = Depends(get_current_active_user),  # Ensure user is authenticated
    storage_service: StorageService = Depends(get_storage_service)
):
    """Generate a signed URL for downloading a file."""
    try:
        signed_url = storage_service.generate_download_url(
            filename=request.filename
        )
        
        expires_at = (datetime.now(timezone.utc)+ timedelta(minutes=15)).isoformat() + "Z"
        
        return SignedUrlResponse(
            signed_url=signed_url,
            expires_at=expires_at,
            filename=request.filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate download URL: {str(e)}"
        )

@router.get("/file-exists/{filename:path}")
async def check_file_exists(
    filename: str,
    current_user = Depends(get_current_active_user),
    storage_service: StorageService = Depends(get_storage_service)
):
    """Check if a file exists in storage."""
    exists = storage_service.file_exists(filename)
    return {"exists": exists, "filename": filename}