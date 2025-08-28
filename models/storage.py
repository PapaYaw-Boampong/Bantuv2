from sqlmodel import SQLModel, Field, Column, DateTime
import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta


class MediaFile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: str  # 'audio' or 'image'
    url: str
    file_name: str
    mime_type: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
