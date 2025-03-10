import uuid

from sqlmodel import SQLModel, Field


class ModelMetadata(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    model_name: str
    model_version: str
    dataset_used: str
    created_at: str

