import uuid

from sqlmodel import SQLModel, Field, Relationship
# from models.user import User


class Storage(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    file_url: str
    file_size: int
    uploaded_at: str

    user: "User" = Relationship(back_populates="storage")



