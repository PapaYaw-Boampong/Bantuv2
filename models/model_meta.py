from sqlmodel import SQLModel, Field


class ModelMetadata(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    model_name: str
    model_version: str
    dataset_used: str
    created_at: str

