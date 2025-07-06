
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from sqlmodel import Field, SQLModel, Relationship, Column,DateTime
import secrets
import uuid

if TYPE_CHECKING:
    from models import User


class RefreshToken(SQLModel, table=True):
    """Refresh token model for user sessions"""
    __tablename__ = "refresh_token"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )

    # Store a unique identifier that doesn't expose the actual token
    token_hash: str = Field(index=True, unique=True)

    # User information
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    user: "User" = Relationship(back_populates="refresh_tokens")

    # Device and security information
    device_info: Optional[str] = None
    ip_address: Optional[str] = None

    # Token usage and rotation tracking
    last_used_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    
    rotations_count: int = Field(default=0)

    # Status flags
    is_revoked: bool = Field(default=False)

    revoked_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    revoked_reason: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def needs_rotation(self) -> bool:
        # Rotate after 7 days or 5 uses, whichever comes first
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        return (self.issued_at < seven_days_ago) or (self.rotations_count >= 5)
