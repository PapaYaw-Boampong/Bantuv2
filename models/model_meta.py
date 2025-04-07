import uuid

from sqlmodel import SQLModel, Field


class ModelMetadata(SQLModel, table=True):
    """Metadata for models used in the platform"""
    __tablename__ = "model_metadata"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    model_name: str
    model_version: str
    dataset_used: str
    created_at: str

