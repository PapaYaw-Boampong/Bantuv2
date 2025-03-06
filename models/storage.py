from sqlmodel import SQLModel, Field, Relationship
from user import User


class Storage(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id")
    file_url: str
    file_size: int
    uploaded_at: str

    user: "User" = Relationship()