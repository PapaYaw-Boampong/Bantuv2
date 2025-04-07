import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService
from crud.user import UserCrud
from models.user import User
from services.token_service import TokenService, get_password_hash, verify_password


# Fixtures
@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user_crud():
    mock = AsyncMock(spec=UserCrud)
    return mock


@pytest.fixture
def user_service(mock_db, mock_user_crud):
    with patch('services.user_service.UserCrud', return_value=mock_user_crud):
        service = UserService(mock_db)
        return service


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user123"
    user.username = "testuser"
    user.fullname = "Test User"
    user.email = "test@example.com"
    user.is_active = True
    user.role = "user"
    user.updated_at = "2023-01-01T00:00:00"
    user.created_at = "2023-01-01T00:00:00"
    user.contribution_count = 10
    user.accepted_contributions = 8
    user.reputation_score = 85
    user.total_hours_speech = 5
    user.total_sentences_translated = 100
    user.total_tokens_produced = 1000
    user.total_points = 200
    user.hashed_password = get_password_hash("password123")
    return user


# Tests
class TestUserService:
    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = None
        mock_user_crud.create.return_value = MagicMock()

        with patch('services.user_service.get_password_hash', return_value="hashed_password"):
            with patch('services.user_service.TokenService'):
                # Act
                result = await user_service.register_user(
                    username="newuser",
                    email="new@example.com",
                    password="password123",
                    fullname="New User",
                    country="US"
                )

                # Assert
                mock_user_crud.get_by_username.assert_called_once_with("newuser")
                mock_user_crud.get_by_email.assert_called_once_with("new@example.com")
                mock_user_crud.create.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_register_user_username_exists(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_username.return_value = mock_user

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:

            await user_service.register_user(
                username="testuser",
                email="new@example.com",
                password="password123",
                fullname="New User",
                country="US"
            )

        assert exc_info.value.status_code == 400
        assert "Username already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = mock_user

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.register_user(
                username="newuser",
                email="test@example.com",
                password="password123",
                fullname="New User",
                country="US"
            )

        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authenticate_user_by_username_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_username.return_value = mock_user

        with patch('services.user_service.verify_password', return_value=True):
            # Act
            result = await user_service.authenticate_user("testuser", "password123")

            # Assert
            assert result is not None
            assert result.username == "testuser"
            mock_user_crud.get_by_username.assert_called_once_with("testuser")
            mock_user_crud.get_by_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_user_by_email_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = mock_user

        with patch('services.user_service.verify_password', return_value=True):
            # Act
            result = await user_service.authenticate_user("test@example.com", "password123")

            # Assert
            assert result is not None
            assert result.email == "test@example.com"
            mock_user_crud.get_by_username.assert_called_once_with("test@example.com")
            mock_user_crud.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_authenticate_user_fail_not_found(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = None

        # Act
        result = await user_service.authenticate_user("nonexistent", "password123")

        # Assert
        assert result is None
        mock_user_crud.get_by_username.assert_called_once_with("nonexistent")
        mock_user_crud.get_by_email.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_authenticate_user_fail_inactive(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user = mock_user
        mock_user.is_active = False
        mock_user_crud.get_by_username.return_value = mock_user

        # Act
        result = await user_service.authenticate_user("testuser", "password123")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_fail_wrong_password(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_username.return_value = mock_user

        with patch('services.user_service.verify_password', return_value=False):
            # Act
            result = await user_service.authenticate_user("testuser", "wrongpassword")

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_id.return_value = mock_user

        # Act
        result = await user_service.get_user_profile("user123")

        # Assert
        assert result["id"] == "user123"
        assert result["username"] == "testuser"
        assert result["acceptance_rate"] == 80.0  # 8/10 * 100
        mock_user_crud.get_by_id.assert_called_once_with("user123")
        mock_user_crud.calculate_reputation_score.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.get_user_profile("nonexistent")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_id.return_value = mock_user

        # Act
        result = await user_service.get_user_by_id("user123")

        # Assert
        assert result == mock_user
        mock_user_crud.get_by_id.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.update.return_value = mock_user
        update_data = {
            "fullname": "Updated Name",
            "country": "UK",
            "hashed_password": "should_be_removed",
            "role": "should_be_removed"
        }

        # Act
        result = await user_service.update_user_profile("user123", update_data)

        # Assert
        assert result == mock_user
        # Check that protected fields were removed
        update_data_passed = mock_user_crud.update.call_args[0][1]
        assert "hashed_password" not in update_data_passed
        assert "role" not in update_data_passed
        assert update_data_passed["fullname"] == "Updated Name"
        assert update_data_passed["country"] == "UK"

    @pytest.mark.asyncio
    async def test_update_user_profile_not_found(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.update.return_value = None
        update_data = {"fullname": "Updated Name"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user_profile("nonexistent", update_data)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_id.return_value = mock_user
        mock_user_crud.update.return_value = mock_user

        with patch('services.user_service.verify_password', return_value=True), \
                patch('services.user_service.get_password_hash', return_value="new_hashed_password"), \
                patch('services.user_service.TokenService'):
            # Act
            result = await user_service.change_password("user123", "current_password", "new_password")

            # Assert
            assert result is True
            mock_user_crud.update.assert_called_once_with("user123", {"hashed_password": "new_hashed_password"})

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.change_password("nonexistent", "current_password", "new_password")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current_password(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.get_by_id.return_value = mock_user

        with patch('services.user_service.verify_password', return_value=False):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await user_service.change_password("user123", "wrong_password", "new_password")

            assert exc_info.value.status_code == 400
            assert "Incorrect current password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.update.return_value = mock_user

        # Act
        result = await user_service.deactivate_user("user123")

        # Assert
        assert result == mock_user
        mock_user_crud.update.assert_called_once_with("user123", {"is_active": False})

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.update.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.deactivate_user("nonexistent")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_top_contributors(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_users = [mock_user for _ in range(5)]
        mock_user_crud.get_all.return_value = mock_users

        # Act
        result = await user_service.get_top_contributors(limit=3)

        # Assert
        assert len(result) == 3
        assert result[0]["username"] == "testuser"
        assert result[0]["reputation_score"] == 85
        mock_user_crud.get_all.assert_called_once_with(limit=100)

    @pytest.mark.asyncio
    async def test_record_contribution_activity_success(self, user_service, mock_user_crud, mock_user):
        # Arrange
        mock_user_crud.increment_contribution_stats.return_value = mock_user

        # Act
        result = await user_service.record_contribution_activity(
            user_id="user123",
            is_accepted=True,
            hours_speech=2,
            sentences_translated=50,
            tokens_produced=500,
            points=100
        )

        # Assert
        assert result == mock_user
        mock_user_crud.increment_contribution_stats.assert_called_once_with(
            user_id="user123",
            is_accepted=True,
            hours_speech=2,
            sentences_translated=50,
            tokens_produced=500,
            points=100
        )
        mock_user_crud.calculate_reputation_score.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_record_contribution_activity_user_not_found(self, user_service, mock_user_crud):
        # Arrange
        mock_user_crud.increment_contribution_stats.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await user_service.record_contribution_activity(user_id="nonexistent")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail