import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from models.language import Language, UserLanguage
from services.language_service import LanguageService


# Mock data
@pytest.fixture
def mock_language():
    """Create a mock Language object"""
    language = MagicMock()
    language.id = uuid.uuid4()
    language.name = "English"
    language.code = "eng"
    language.description = "English language"
    return language


@pytest.fixture
def mock_user_language(mock_language):
    """Create a mock UserLanguage object"""
    user_language = MagicMock()
    user_language.id = uuid.uuid4()
    user_language.user_id = uuid.uuid4()
    user_language.language_id = mock_language.id
    user_language.language = mock_language
    user_language.proficiency = "Advanced"
    return user_language


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_language_crud():
    """Create a mock LanguageCrud"""
    crud = AsyncMock()
    return crud


@pytest.fixture
def mock_user_language_crud():
    """Create a mock UserLanguageCrud"""
    crud = AsyncMock()
    return crud


@pytest.fixture
def language_service(mock_db, mock_language_crud, mock_user_language_crud):
    """Create a LanguageService with mocked dependencies"""
    service = LanguageService(mock_db)
    service.language_repository = mock_language_crud
    service.user_language_repository = mock_user_language_crud
    return service


# Tests for Language operations
@pytest.mark.asyncio
async def test_create_language_success(language_service, mock_language):
    """Test creating a language successfully"""
    # Setup
    language_data = {
        "name": "Spanish",
        "code": "spa",
        "description": "Spanish language"
    }
    language_service.language_repository.get_by_code.return_value = None
    language_service.language_repository.create.return_value = mock_language

    # Execute
    result = await language_service.create_language(language_data)

    # Assert
    assert result == mock_language
    language_service.language_repository.get_by_code.assert_called_once_with("spa")
    language_service.language_repository.create.assert_called_once_with(language_data)


@pytest.mark.asyncio
async def test_create_language_already_exists(language_service, mock_language):
    """Test creating a language that already exists"""
    # Setup
    language_data = {
        "name": "English",
        "code": "eng",
        "description": "English language"
    }
    language_service.language_repository.get_by_code.return_value = mock_language

    # Execute and Assert
    with pytest.raises(HTTPException) as excinfo:
        await language_service.create_language(language_data)

    assert excinfo.value.status_code == 400
    assert "already exists" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_language_by_id(language_service, mock_language):
    """Test getting a language by ID"""
    # Setup
    language_id = "123"
    language_service.language_repository.get_by_id.return_value = mock_language

    # Execute
    result = await language_service.get_language(language_id)

    # Assert
    assert result == mock_language
    language_service.language_repository.get_by_id.assert_called_once_with(language_id)


@pytest.mark.asyncio
async def test_get_language_by_code(language_service, mock_language):
    """Test getting a language by code"""
    # Setup
    language_code = "eng"
    language_service.language_repository.get_by_code.return_value = mock_language

    # Execute
    result = await language_service.get_language(language_code)

    # Assert
    assert result == mock_language
    language_service.language_repository.get_by_code.assert_called_once_with(language_code)


@pytest.mark.asyncio
async def test_get_language_by_name(language_service, mock_language):
    """Test getting a language by name"""
    # Setup
    language_name = "English"
    language_service.language_repository.get_by_name.return_value = mock_language

    # Execute
    result = await language_service.get_language(language_name)

    # Assert
    assert result == mock_language
    language_service.language_repository.get_by_name.assert_called_once_with(language_name)


@pytest.mark.asyncio
async def test_get_language_not_found(language_service):
    """Test getting a non-existent language"""
    # Setup
    language_service.language_repository.get_by_id.return_value = None

    # Execute and Assert
    with pytest.raises(HTTPException) as excinfo:
        await language_service.get_language("123")

    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_all_languages(language_service, mock_language):
    """Test getting all languages"""
    # Setup
    languages = [mock_language, mock_language]
    language_service.language_repository.get_all.return_value = languages

    # Execute
    result = await language_service.get_all_languages()

    # Assert
    assert result == languages
    language_service.language_repository.get_all.assert_called_once_with(0, 100)


@pytest.mark.asyncio
async def test_get_all_languages_empty(language_service):
    """Test getting all languages when none exist"""
    # Setup
    language_service.language_repository.get_all.return_value = []

    # Execute
    result = await language_service.get_all_languages()

    # Assert
    assert result == []
    language_service.language_repository.get_all.assert_called_once_with(0, 100)


@pytest.mark.asyncio
async def test_update_language_success(language_service, mock_language):
    """Test updating a language successfully"""
    # Setup
    language_id = str(uuid.uuid4())
    update_data = {"name": "Updated English"}
    language_service.language_repository.update.return_value = mock_language

    # Execute
    result = await language_service.update_language(language_id, update_data)

    # Assert
    assert result == mock_language
    language_service.language_repository.update.assert_called_once_with(language_id, update_data)


@pytest.mark.asyncio
async def test_update_language_not_found(language_service):
    """Test updating a non-existent language"""
    # Setup
    language_id = str(uuid.uuid4())
    update_data = {"name": "Updated English"}
    language_service.language_repository.update.return_value = None

    # Execute and Assert
    with pytest.raises(HTTPException) as excinfo:
        await language_service.update_language(language_id, update_data)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_language_success(language_service):
    """Test deleting a language successfully"""
    # Setup
    language_id = str(uuid.uuid4())
    language_service.language_repository.delete.return_value = True

    # Execute
    result = await language_service.delete_language(language_id)

    # Assert
    assert result is True
    language_service.language_repository.delete.assert_called_once_with(language_id)


@pytest.mark.asyncio
async def test_delete_language_not_found(language_service):
    """Test deleting a non-existent language"""
    # Setup
    language_id = str(uuid.uuid4())
    language_service.language_repository.delete.return_value = False

    # Execute and Assert
    with pytest.raises(HTTPException) as excinfo:
        await language_service.delete_language(language_id)

    assert excinfo.value.status_code == 404


# Tests for User-Language operations
@pytest.mark.asyncio
async def test_add_user_language_success(language_service, mock_user_language):
    """Test adding a language to a user successfully"""
    # Setup
    user_id = str(uuid.uuid4())
    language_id = str(uuid.uuid4())
    proficiency = "Advanced"

    language_service.user_language_repository.create.return_value = mock_user_language
    language_service.user_language_repository.get_by_id.return_value = mock_user_language

    # Execute
    result = await language_service.add_user_language(user_id, language_id, proficiency)

    # Assert
    assert result["association_id"] == str(mock_user_language.id)
    assert result["proficiency"] == str(mock_user_language.proficiency)
    assert result["language"]["id"] == str(mock_user_language.language.id)
    assert result["language"]["name"] == mock_user_language.language.name

    expected_data = {"user_id": user_id, "language_id": language_id, "proficiency": proficiency}
    language_service.user_language_repository.create.assert_called_once_with(expected_data)


@pytest.mark.asyncio
async def test_add_user_language_integrity_error(language_service):
    """Test adding a language to a user with an integrity error"""
    # Setup
    user_id = str(uuid.uuid4())
    language_id = str(uuid.uuid4())
    proficiency = "Advanced"

    language_service.user_language_repository.create.side_effect = IntegrityError(
        statement=None, params=None, orig=None
    )

    # Execute and Assert
    with pytest.raises(HTTPException) as excinfo:
        await language_service.add_user_language(user_id, language_id, proficiency)

    assert excinfo.value.status_code == 400
    assert "already exists" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_user_languages(language_service, mock_user_language):
    """Test getting all languages for a user"""
    # Setup
    user_id = str(uuid.uuid4())
    language_service.user_language_repository.get_languages_by_user.return_value = [mock_user_language]

    # Execute
    result = await language_service.get_user_languages(user_id)

    # Assert
    assert len(result) == 1
    assert result[0]["association_id"] == str(mock_user_language.id)
    assert result[0]["proficiency"] == mock_user_language.proficiency
    assert result[0]["language"]["id"] == str(mock_user_language.language.id)
    language_service.user_language_repository.get_languages_by_user.assert_called_once_with(user_id, 0, 100)


@pytest.mark.asyncio
async def test_remove_user_language_success(language_service):
    """Test removing a language from a user successfully"""
    # Setup
    user_language_id = str(uuid.uuid4())
    language_service.user_language_repository.delete.return_value = True

    # Execute
    result = await language_service.remove_user_language(user_language_id)

    # Assert
    assert result is True
    language_service.user_language_repository.delete.assert_called_once_with(user_language_id)


@pytest.mark.asyncio
async def test_remove_user_language_not_found(language_service):
    """Test removing a non-existent user-language association"""
    # Setup
    user_language_id = str(uuid.uuid4())
    language_service.user_language_repository.delete.return_value = False

    # Execute and Assert
    with pytest.raises(HTTPException) as excinfo:
        await language_service.remove_user_language(user_language_id)

    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_speech_hours(language_service, mock_user_language):
    """Test updating speech hours"""
    # Setup
    user_id = str(uuid.uuid4())
    language_id = str(uuid.uuid4())
    hours = 10
    language_service.user_language_repository.update_speech_hours.return_value = mock_user_language

    # Execute
    result = await language_service.update_speech_hours(user_id, language_id, hours)

    # Assert
    assert result == mock_user_language
    language_service.user_language_repository.update_speech_hours.assert_called_once_with(user_id, language_id, hours)


@pytest.mark.asyncio
async def test_update_sentences_translated(language_service, mock_user_language):
    """Test updating sentences translated"""
    # Setup
    user_id = str(uuid.uuid4())
    language_id = str(uuid.uuid4())
    sentences = 100
    language_service.user_language_repository.update_sentences_translated.return_value = mock_user_language

    # Execute
    result = await language_service.update_sentences_translated(user_id, language_id, sentences)

    # Assert
    assert result == mock_user_language
    language_service.user_language_repository.update_sentences_translated.assert_called_once_with(
        user_id, language_id, sentences
    )