from datetime import datetime, timedelta
import time
from typing import Dict, Union
from sqlmodel import select
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
import os
import uuid
import secrets
import hashlib
from fastapi import HTTPException, status
from models import User, RefreshToken

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password verification",
        ) from e


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def _hash_token(token: str) -> str:
    """Create a secure hash of the token for database storage"""
    return hashlib.sha256(token.encode()).hexdigest()


class TokenService:
    def __init__(
            self,
            db_session: AsyncSession,
            access_secret_key: str = os.getenv("ACCESS_SECRET_KEY", "your_default_secret_key"),
            refresh_secret_key: str = os.getenv("REFRESH_SECRET_KEY", "your_other_default_refresh_secret_key"),
            algorithm: str = os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)),
            refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    ):
        self.db = db_session
        self.access_secret_key = access_secret_key
        self.refresh_secret_key = refresh_secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    # Password utilities

    # Token creation methods
    async def create_tokens(
            self,
            user_id: str,
            device_info: str = None,
            ip_address: str = None,
            user_agent: str = None
    ) -> Dict[str, str]:
        """Create both access and refresh tokens for a user"""
        # Create access token using JWT
        access_token = self._create_access_token(user_id)

        # Create refresh token
        token_value = secrets.token_hex(64)  # 128 character random string
        token_hash = _hash_token(token_value)

        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        # Create database record for refresh token
        refresh_token_record = RefreshToken(
            token_hash=token_hash,
            user_id=uuid.UUID(user_id),
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )

        # Save to database asynchronously
        self.db.add(refresh_token_record)
        await self.db.commit()
        await self.db.refresh(refresh_token_record)

        return {
            "access_token": access_token,
            "refresh_token": token_value,  # Return actual token to client
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60  # in seconds
        }

    async def refresh_tokens(
            self,
            refresh_token: str,
            ip_address: str = None
    ) -> Dict[str, str]:
        """
        Use a refresh token to get a new access token
        and possibly rotate the refresh token
        """

        # Now check if it exists in the database and is valid
        token_hash = _hash_token(refresh_token)

        # Find the token in the database asynchronously
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(statement)
        db_token = result.scalar_one_or_none()

        if not db_token or db_token.is_revoked or db_token.is_expired:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last used time
        db_token.last_used_at = datetime.utcnow()

        # Get the user asynchronously
        statement = select(User).where(User.id == db_token.user_id)
        result = await self.db.execute(statement)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive or deleted",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = str(user.id)

        # Create new access token
        access_token = self._create_access_token(user_id)

        # Check if we need to rotate the refresh token
        # Rotate after 7 days or 5 uses, whichever comes first
        should_rotate = False
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        if db_token.issued_at < seven_days_ago or db_token.rotations_count >= 5:
            should_rotate = True

        if should_rotate:
            # Revoke old token
            db_token.is_revoked = True
            db_token.revoked_at = datetime.utcnow()
            db_token.revoked_reason = "Rotation"

            # Create new refresh token
            # new_refresh_token = self._create_refresh_token(user_id)
            new_refresh_token = secrets.token_hex(64)  # 128-character random string

            new_token_hash = _hash_token(new_refresh_token)

            new_refresh_token_record = RefreshToken(
                token_hash=new_token_hash,
                user_id=user.id,
                device_info=db_token.device_info,
                ip_address=ip_address or db_token.ip_address,
                user_agent=db_token.user_agent,
                expires_at=datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
                rotations_count=0
            )

            self.db.add(new_refresh_token_record)
            await self.db.commit()

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60  # in seconds
            }
        else:
            # Increase rotation count every time the token is reused
            db_token.rotations_count += 1
            await self.db.commit()

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,  # Return the same refresh token
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60  # in seconds
            }

    async def revoke_refresh_token(self, refresh_token: str, reason: str = "User logout") -> bool:
        """Revoke a specific refresh token"""
        try:
            # # Verify the token JWT
            # self.decode_token(refresh_token, is_refresh=True)

            # Get the token hash
            token_hash = _hash_token(refresh_token)

            # Find and revoke the token asynchronously
            statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            result = await self.db.execute(statement)
            db_token = result.scalar_one_or_none()

            if not db_token:
                return False

            db_token.is_revoked = True
            db_token.revoked_at = datetime.utcnow()
            db_token.revoked_reason = reason

            await self.db.commit()
            return True
        except (HTTPException, JWTError):
            # If token is invalid, just return False
            return False

    async def revoke_all_user_tokens(self, user_id: str, reason: str = "Security logout") -> int:
        """Revoke all refresh tokens for a user"""
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
        result = await self.db.execute(statement)
        tokens = result.scalars().all()

        if not tokens:
            return 0  # No tokens to revoke

        count = 0
        for token in tokens:
            token.is_revoked = True
            token.revoked_at = datetime.utcnow()
            token.revoked_reason = reason
            count += 1

        await self.db.commit()
        return count

    # JWT token methods (unchanged since they don't interact with the database)
    def _create_access_token(self, subject: Union[str, int]) -> str:
        """Create a JWT access token (short-lived)"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "access",
            "iat": datetime.utcnow()
        }

        # Convert datetime to Unix timestamp
        to_encode["iat"] = int(to_encode["iat"].timestamp())  # Convert 'iat' to timestamp
        to_encode["exp"] = int(to_encode["exp"].timestamp())  # Convert 'exp' to timestamp

        encoded_jwt = jwt.encode(to_encode, self.access_secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def _create_refresh_token(self, subject: Union[str, int]) -> str:
        """Create a JWT refresh token (long-lived)"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode = {
            "exp": expire,
            "sub": str(subject),
            "type": "refresh",
            "iat": datetime.utcnow()
        }

        # Convert datetime to Unix timestamp
        to_encode["iat"] = int(to_encode["iat"].timestamp())  # Convert 'iat' to timestamp
        to_encode["exp"] = int(to_encode["exp"].timestamp())  # Convert 'exp' to timestamp

        encoded_jwt = jwt.encode(to_encode, self.refresh_secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str, is_refresh: bool = False) -> dict:
        """
        Decode and validate a JWT token.
        Distinguishes between access and refresh tokens.
        """
        try:
            secret_key = self.access_secret_key
            payload = jwt.decode(token, secret_key, algorithms=[self.algorithm])

            token_type = payload.get("type")
            expected_type = "access"

            if token_type != expected_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token. Expected {expected_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
