from pydantic import BaseModel
from typing import List
from uuid import UUID


# class MediaFileRead(BaseModel):
#     id: UUID
#     type: str
#     url: str
#     file_name: str
#     mime_type: str


# class MediaFileCreate(BaseModel):
#     type: str
#     url: str
#     file_name: str
#     mime_type: str



from pydantic import BaseModel
from typing import Literal

class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str

class DownloadUrlRequest(BaseModel):
    filename: str

class SignedUrlResponse(BaseModel):
    signed_url: str
    expires_at: str
    filename: str
