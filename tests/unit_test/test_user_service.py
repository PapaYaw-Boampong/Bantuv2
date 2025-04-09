import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService
from crud.user import UserCrud
from services.token_service import get_password_hash


# Fixtures
@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user_crud():
    return AsyncMock(spec=UserCrud)


@pytest.fixture
def user_service(mock_db, mock_user_crud):
    with patch('services.user_service.UserCrud', return_value=mock_user_crud):
        return UserService(mock_db)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.hashed_password = get_password_hash("password123")
    return user


# Test class
class TestUserService:
    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service, mock_user_crud):
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = None
        mock_user_crud.create.return_value = MagicMock()

        with patch('services.user_service.get_password_hash', return_value="hashed_password"), \
             patch('services.user_service.TokenService'):
            result = await user_service.register_user(
                username="newuser",
                email="new@example.com",
                password="password123",
                fullname="New User",
                country="US"
            )

            assert result is not None
            mock_user_crud.get_by_username.assert_called_once_with("newuser")
            mock_user_crud.get_by_email.assert_called_once_with("new@example.com")
            mock_user_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_username_exists(self, user_service, mock_user_crud, mock_user):
        mock_user_crud.get_by_username.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            await user_service.register_user(
                username="testuser",
                email="new@example.com",
                password="password123",
                fullname="Test User",
                country="GH"
            )

        assert exc_info.value.status_code == 400
        assert "Username already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, user_service, mock_user_crud, mock_user):
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            await user_service.register_user(
                username="uniqueuser",
                email="test@example.com",
                password="password123",
                fullname="Another User",
                country="GH"
            )

        assert exc_info.value.status_code == 400
        assert "Email already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_authenticate_user_username_success(self, user_service, mock_user_crud, mock_user):
        mock_user_crud.get_by_username.return_value = mock_user
        with patch('services.user_service.verify_password', return_value=True):
            result = await user_service.authenticate_user("testuser", "password123")
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_authenticate_user_email_success(self, user_service, mock_user_crud, mock_user):
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = mock_user
        with patch('services.user_service.verify_password', return_value=True):
            result = await user_service.authenticate_user("test@example.com", "password123")
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_authenticate_user_fail_not_found(self, user_service, mock_user_crud):
        mock_user_crud.get_by_username.return_value = None
        mock_user_crud.get_by_email.return_value = None
        result = await user_service.authenticate_user("ghost", "pass")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_fail_wrong_password(self, user_service, mock_user_crud, mock_user):
        mock_user_crud.get_by_username.return_value = mock_user
        with patch('services.user_service.verify_password', return_value=False):
            result = await user_service.authenticate_user("testuser", "wrongpass")
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, user_service, mock_user_crud, mock_user):
        mock_user.is_active = False
        mock_user_crud.get_by_username.return_value = mock_user
        result = await user_service.authenticate_user("testuser", "password123")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_user_crud, mock_user):
        update_payload = {
            "fullname": "Updated User",
            "country": "NG",
            "role": "admin",  # should be stripped
            "hashed_password": "fake_hash"  # should be stripped
        }
        mock_user_crud.update_profile.return_value = mock_user

        result = await user_service.update_user_profile("user123", update_payload)
        assert result == mock_user

        sent_update_data = mock_user_crud.update_profile.call_args[0][1]
        assert "role" not in sent_update_data
        assert "hashed_password" not in sent_update_data

    @pytest.mark.asyncio
    async def test_update_user_profile_user_not_found(self, user_service, mock_user_crud):
        mock_user_crud.update_profile.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await user_service.update_user_profile("missing", {"fullname": "New Name"})

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_user_crud, mock_user):
        mock_user_crud.update_profile.return_value = mock_user

        with patch('services.user_service.verify_password', return_value=True), \
             patch('services.user_service.get_password_hash', return_value="new_hash"), \
             patch('services.user_service.TokenService'):
            result = await user_service.change_password(mock_user, "password123", "newpass")
            assert result is True
            mock_user_crud.update_profile.assert_called_once_with(str(mock_user.id), {"hashed_password": "new_hash"})

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, mock_user):
        with patch('services.user_service.verify_password', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await user_service.change_password(mock_user, "wrongpass", "newpass")
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service, mock_db, mock_user_crud, mock_user):
        mock_user_crud.update_profile.return_value = mock_user

        result = await user_service.deactivate_user("user123")

        assert result == mock_user
        mock_user_crud.update_profile.assert_called_once_with("user123", {"is_active": False})

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(self, user_service, mock_user_crud):
        mock_user_crud.update_profile.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await user_service.deactivate_user("nonexistent_id")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"\


    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_db, mock_user):
        user_service.get_detailed_user_by_id = AsyncMock(return_value=mock_user)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        result = await user_service.delete("user123")

        assert result is True
        user_service.get_detailed_user_by_id.assert_awaited_once_with("user123")
        mock_db.delete.assert_awaited_once_with(mock_user)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service, mock_db):
        user_service.get_detailed_user_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await user_service.delete("nonexistent_id")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"\
