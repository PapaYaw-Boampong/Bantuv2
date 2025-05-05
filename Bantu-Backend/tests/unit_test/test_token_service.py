import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from jose import jwt, JWTError
from fastapi import HTTPException
import hashlib
import os

from models import User, RefreshToken
from services.token_service import TokenService, verify_password, get_password_hash, _hash_token


# Setup test fixtures
@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def token_service(mock_db):
    """Create a TokenService instance with mock DB and test settings."""
    return TokenService(
        db_session=mock_db,
        access_secret_key="test_access_key",
        refresh_secret_key="test_refresh_key",
        algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7
    )


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_user(test_user_id):
    """Create a mock User object."""
    user = MagicMock()
    user.id = uuid.UUID(test_user_id)
    user.is_active = True
    return user


@pytest.fixture
def mock_refresh_token():
    """Create a mock RefreshToken object."""
    token = MagicMock()
    token.is_revoked = False
    token.is_expired = False
    token.issued_at = datetime.utcnow()
    token.rotations_count = 0
    token.device_info = "test_device"
    token.ip_address = "127.0.0.1"
    token.user_agent = "test_agent"
    return token


# Tests for utility functions
def test_verify_password():
    """Test password verification."""
    password = "test_password"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_get_password_hash():
    """Test password hashing."""
    password = "test_password"
    hashed = get_password_hash(password)

    assert hashed != password
    assert hashed.startswith("$2b$")  # Check for bcrypt hash format


def test_hash_token():
    """Test token hashing."""
    token = "test_token"
    hashed = _hash_token(token)

    assert hashed == hashlib.sha256(token.encode()).hexdigest()


# TokenService tests
@pytest.mark.asyncio
async def test_create_tokens(token_service, test_user_id, mock_db):
    """Test creating access and refresh tokens."""
    tokens = await token_service.create_tokens(
        test_user_id,
        device_info="test_device",
        ip_address="127.0.0.1",
        user_agent="test_agent"
    )

    # Check correct token formats were returned
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "token_type" in tokens
    assert "expires_in" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60  # 15 minutes in seconds

    # Verify token was added to database
    assert mock_db.add.called
    assert mock_db.commit.called
    assert mock_db.refresh.called

    # Test token validity
    payload = jwt.decode(
        tokens["access_token"],
        "test_access_key",
        algorithms=["HS256"]
    )
    assert payload["sub"] == test_user_id
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_refresh_tokens_no_rotation(token_service, test_user_id, mock_db, mock_refresh_token, mock_user):
    """Test refreshing tokens without token rotation."""
    refresh_token = "test_refresh_token"
    token_hash = _hash_token(refresh_token)

    # Mock the result object that scalar_one_or_none() is called on
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.side_effect = [mock_refresh_token, mock_user]

    # Make mock_db.execute an async function that returns result_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Set token rotation parameters to avoid rotation
    mock_refresh_token.issued_at = datetime.utcnow() - timedelta(days=1)
    mock_refresh_token.rotations_count = 2
    mock_refresh_token.user_id = uuid.UUID(test_user_id)

    # Call refresh tokens method
    tokens = await token_service.refresh_tokens(refresh_token, "127.0.0.1")

    # Check results
    assert tokens["refresh_token"] == refresh_token  # Same token returned
    assert mock_refresh_token.rotations_count == 3  # Rotation count increased
    assert mock_db.commit.called

    # Verify access token is valid
    payload = jwt.decode(
        tokens["access_token"],
        "test_access_key",
        algorithms=["HS256"]
    )
    assert payload["sub"] == test_user_id
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_refresh_tokens_with_rotation(token_service, test_user_id, mock_db, mock_refresh_token, mock_user):
    """Test refreshing tokens with token rotation."""
    refresh_token = "test_refresh_token"
    token_hash = _hash_token(refresh_token)

    # Set up database return values
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_refresh_token

    user_result_mock = MagicMock()
    user_result_mock.scalar_one_or_none.return_value = mock_user

    # Fix: Mock both DB calls using side_effect
    mock_db.execute = AsyncMock(side_effect=[result_mock, user_result_mock])

    # Set token rotation parameters to trigger rotation
    mock_refresh_token.issued_at = datetime.utcnow() - timedelta(days=10)  # Older than 7 days
    mock_refresh_token.rotations_count = 2
    mock_refresh_token.user_id = uuid.UUID(test_user_id)
    mock_refresh_token.is_revoked = False
    mock_refresh_token.is_expired = False

    # Call refresh tokens method
    tokens = await token_service.refresh_tokens(refresh_token, "127.0.0.1")

    # Check results
    assert tokens["refresh_token"] != refresh_token  # New token returned
    assert mock_refresh_token.is_revoked is True  # Old token revoked
    assert mock_refresh_token.revoked_reason == "Rotation"
    assert mock_db.add.called  # New token added to DB
    assert mock_db.commit.called

    # Verify access token is valid
    payload = jwt.decode(
        tokens["access_token"],
        "test_access_key",
        algorithms=["HS256"]
    )
    assert payload["sub"] == test_user_id
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_refresh_tokens_inactive_user(token_service, test_user_id, mock_db, mock_refresh_token, mock_user):
    """Test refreshing tokens with an inactive user."""
    refresh_token = "test_refresh_token"

    # Set up database return values
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.side_effect = [mock_refresh_token, mock_user]

    # Make mock_db.execute an async function that returns result_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Set user as inactive
    mock_user.is_active = False
    mock_refresh_token.user_id = uuid.UUID(test_user_id)

    # Check that the function raises HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await token_service.refresh_tokens(refresh_token, "127.0.0.1")

    assert excinfo.value.status_code == 401
    assert "User is inactive or deleted" in excinfo.value.detail


@pytest.mark.asyncio
async def test_refresh_tokens_expired_token(token_service, mock_db, mock_refresh_token):
    """Test refreshing with an expired token."""
    refresh_token = "test_refresh_token"

    # Set up database return values
    result_mock = MagicMock()
    mock_refresh_token.is_expired = True
    result_mock.scalar_one_or_none.return_value = mock_refresh_token

    mock_db.execute = AsyncMock(return_value=result_mock)

    # Check that the function raises HTTPException
    with pytest.raises(HTTPException) as excinfo:
        await token_service.refresh_tokens(refresh_token, "127.0.0.1")

    assert excinfo.value.status_code == 401
    assert "Invalid or expired refresh token" in excinfo.value.detail


@pytest.mark.asyncio
async def test_revoke_refresh_token(token_service, mock_db, mock_refresh_token):
    """Test revoking a refresh token."""
    refresh_token = "test_refresh_token"

    # Set up database return values
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_refresh_token

    # Make mock_db.execute an async function that returns result_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Revoke the token
    result = await token_service.revoke_refresh_token(refresh_token, "Test revocation")

    # Check results
    assert result is True
    assert mock_refresh_token.is_revoked is True
    assert mock_refresh_token.revoked_reason == "Test revocation"
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_revoke_nonexistent_token(token_service, mock_db):
    """Test revoking a token that doesn't exist."""
    refresh_token = "nonexistent_token"

    # Set up database to return None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None

    # Make mock_db.execute an async function that returns result_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Revoke the token
    result = await token_service.revoke_refresh_token(refresh_token)

    # Check results
    assert result is False
    assert mock_db.commit.called is False  # Should not commit changes


@pytest.mark.asyncio
async def test_revoke_all_user_tokens(token_service, test_user_id, mock_db):
    """Test revoking all tokens for a user."""
    # Create multiple mock tokens
    token1 = MagicMock()
    token2 = MagicMock()
    token3 = MagicMock()
    tokens = [token1, token2, token3]

    # Set up database return values
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = tokens
    result_mock.scalars.return_value = scalars_mock

    # Make mock_db.execute an async function that returns result_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Revoke all tokens
    count = await token_service.revoke_all_user_tokens(test_user_id, "Security logout")

    # Check results
    assert count == 3
    for token in tokens:
        assert token.is_revoked is True
        assert token.revoked_reason == "Security logout"
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_revoke_all_user_tokens_none_found(token_service, test_user_id, mock_db):
    """Test revoking all tokens when none exist."""
    # Set up database to return empty list
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock.scalars.return_value = scalars_mock
    # Make mock_db.execute an async function that returns result_mock
    mock_db.execute = AsyncMock(return_value=result_mock)

    # Revoke all tokens
    count = await token_service.revoke_all_user_tokens(test_user_id)

    # Check results
    assert count == 0
    assert mock_db.commit.called is False  # Should not commit changes


def test_decode_token_valid(token_service, test_user_id):
    """Test decoding a valid token."""
    # Create a test access token
    access_token = token_service._create_access_token(test_user_id)

    # Decode token
    payload = token_service.decode_token(access_token, is_refresh=False)

    # Check payload
    assert payload["sub"] == test_user_id
    assert payload["type"] == "access"


def test_decode_token_expired(token_service, test_user_id):
    """Test that decoding an expired token raises an HTTPException."""

    # Choose a base time
    fake_now = datetime.utcnow()

    # Patch datetime.utcnow in your token_service module (adjust path if needed)
    with patch('services.token_service.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = fake_now - timedelta(minutes=token_service.access_token_expire_minutes + 1)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Generate a token that's already expired
        expired_token = token_service._create_access_token(test_user_id)

    # Decode the token with the real current time — it should be expired
    with pytest.raises(HTTPException) as exc_info:
        token_service.decode_token(expired_token)

    assert exc_info.value.status_code == 401
    assert "Token has expired" in exc_info.value.detail


def test_decode_token_invalid(token_service):
    """Test decoding an invalid token."""
    # Create an invalid token string
    invalid_token = "invalid.token.string"

    # Check that the function raises HTTPException
    with pytest.raises(HTTPException) as excinfo:
        token_service.decode_token(invalid_token)

    assert excinfo.value.status_code == 401
    assert "Invalid token" in excinfo.value.detail
