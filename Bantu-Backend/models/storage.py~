from sqlmodel import SQLModel, Field
import uuid
from typing import Optional
import datetime


class MediaFile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str  # 'audio' or 'image'
    url: str
    file_name: str
    mime_type: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
