# backend/services/storage.py
import os
import json
from datetime import datetime, timedelta, timezone
from core.config import settings
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account
from fastapi import HTTPException
import logging


logger = logging.getLogger(__name__)

class StorageService:

    def __init__(self):
        self.bucket_name = settings.GCP_BUCKET_NAME
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable is required")
        
        # Initialize GCS client with service account
        self.client = self._init_gcs_client()
        self.bucket = self.client.bucket(self.bucket_name)
        
        # Default expiration time for signed URLs (15 minutes)
        self.url_expiration = timedelta(minutes=15)
    
    def _init_gcs_client(self) -> storage.Client:
        """Initialize Google Cloud Storage client using service account."""
        try:
            # Option 1: Service account key from environment variable (JSON string)
            service_account_info = settings.GCS_SERVICE_ACCOUNT_KEY
            if service_account_info:
                credentials_dict = json.loads(service_account_info)
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict
                )
                return storage.Client(credentials=credentials)
            
            # Option 2: Service account key file path
            service_account_path = settings.GCP_SERVICE_ACCOUNT_KEY_PATH
            if service_account_path and os.path.exists(service_account_path):
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path
                )
                return storage.Client(credentials=credentials)
            
            # Option 3: Default credentials (for Cloud Run, Compute Engine, etc.)
            return storage.Client()
            
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Storage service initialization failed"
            )
    
    def validate_filename(self, filename: str) -> bool:
        """Validate filename follows the expected format."""
        try:
            parts = filename.split('/')
            if len(parts) != 4:
                return False
            
            prefix, task_type, contribution_id, file_part = parts
            
            # Validate format: contributions/{task_type}/{contribution_id}/{timestamp}.{ext}
            if prefix != "contributions":
                return False
            
            if task_type not in ["transcription", "translation", "annotation"]:
                return False
            
            # Basic validation for contribution_id (should be UUID-like or numeric)
            if not contribution_id or len(contribution_id) < 1:
                return False
            
            # Validate file part has extension
            if '.' not in file_part:
                return False
            
            return True
            
        except Exception:
            return False
    
    def generate_upload_url(self, filename: str, content_type: str) -> str:

        """Generate a signed URL for uploading a file."""
        if not self.validate_filename(filename):
            raise HTTPException(
                status_code=400, 
                detail="Invalid filename format"
            )
        
        try:
            blob = self.bucket.blob(filename)
            
            # Generate signed URL for PUT method (upload)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.now(timezone.utc) + self.url_expiration,
                method="PUT",
                content_type=content_type,
                # Prevent public access
                # headers={"x-goog-content-length-range": "0,52428800"}  # Max 50MB
            )
            
            logger.info(f"Generated upload URL for: {filename}")
            return signed_url
            
        except Exception as e:
            logger.error(f"Failed to generate upload URL for {filename}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate upload URL"
            )
    
    def generate_download_url(self, filename: str) -> str:
        """Generate a signed URL for downloading a file."""
        if not self.validate_filename(filename):
            raise HTTPException(
                status_code=400, 
                detail="Invalid filename format"
            )
        
        try:
            blob = self.bucket.blob(filename)
            
            # Check if file exists
            if not blob.exists():
                raise HTTPException(
                    status_code=404, 
                    detail="File not found"
                )
            
            # Generate signed URL for GET method (download)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.now(timezone.utc) + self.url_expiration,
                method="GET"
            )
            
            logger.info(f"Generated download URL for: {filename}")
            return signed_url
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate download URL for {filename}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate download URL"
            )
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from storage (admin function)."""
        if not self.validate_filename(filename):
            raise HTTPException(
                status_code=400, 
                detail="Invalid filename format"
            )
        
        try:
            blob = self.bucket.blob(filename)
            blob.delete()
            logger.info(f"Deleted file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {filename}: {str(e)}")
            return False
    
    def file_exists(self, filename: str) -> bool:

        """Check if a file exists in storage."""
        try:
            blob = self.bucket.blob(filename)
            return blob.exists()
        except Exception:
            return False

    def upload_local_file(self, local_path: str, destination_path: str) -> bool:
        """Upload a local file (from disk) to GCS at the given destination path."""
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(local_path)
            logger.info(f"Uploaded {local_path} to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file {local_path} to {destination_path}: {str(e)}")
            return False
