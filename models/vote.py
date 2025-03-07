from sqlmodel import SQLModel, Field, Relationship

from user import User
from contribution import TranslationContribution, TranscriptionContribution


# ===================== VOTES TABLE =====================
class Vote(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id")
    translation_contribution_id: str = Field(foreign_key="contribution.id")
    transcription_contribution_id: str = Field(foreign_key="contribution.id")
    vote_type: str  # 'upvote' or 'downvote'

    # Relationships
    user: "User" = Relationship(back_populates="votes")
    translation_contribution: "TranslationContribution" = Relationship(back_populates="votes")
    transcription_contribution: "TranscriptionContribution" = Relationship(back_populates="votes")

