from pydantic import BaseModel
from uuid import UUID


class MediaFileRead(BaseModel):
    id: UUID
    type: str
    url: str
    file_name: str
    mime_type: str


class MediaFileCreate(BaseModel):
    type: str
    url: str
    file_name: str
    mime_type: str
