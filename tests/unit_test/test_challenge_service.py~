import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from models.challenge import (
    Challenge, ChallengeParticipation,
    ChallengeStatus, EventType, TaskType, EventCategory
)
from schemas.challenge import (
    ChallengeCreate, ChallengeUpdate, ChallengeParticipationCreate,
    ChallengeParticipationUpdate, GetChallenges
)
from services.challenge_service import ChallengeService


# Fixtures
@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def challenge_service(mock_db):
    service = ChallengeService(mock_db)
    return service


def mock_scalar_result(return_value):
    scalar_mock = MagicMock()
    scalar_mock.all.return_value = return_value
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalar_mock
    return result_mock


challengeid = uuid.uuid4()
participationid = uuid.uuid4()


@pytest.fixture
def mock_challenge():
    challenge = MagicMock(spec=Challenge)
    challenge.id = challengeid
    challenge.challenge_name = "Test Challenge"
    challenge.description = "Test Description"
    challenge.event_type = EventType.DATA_COLLECTION
    challenge.task_type = TaskType.TRANSCRIPTION
    challenge.event_category = EventCategory.COMPETITION
    challenge.start_date = datetime.utcnow() - timedelta(days=1)
    challenge.end_date = datetime.utcnow() + timedelta(days=1)
    challenge.status = ChallengeStatus.ACTIVE
    challenge.is_public = True
    challenge.is_published = True
    challenge.reward = 100
    challenge.participant_count = 5
    challenge.contribution_count = 10
    return challenge


@pytest.fixture
def mock_participation():
    participation = MagicMock(spec=ChallengeParticipation)
    participation.event_id = challengeid
    participation.user_id = participationid
    participation.joined_at = datetime.utcnow()
    participation.updated_at = datetime.utcnow()
    participation.total_points = 50
    participation.total_hours_speech = 5
    participation.total_sentences_translated = 100
    participation.total_tokens_produced = 1000
    participation.acceptance_rate = 80.0
    return participation


# Tests
class TestChallengeService:

    # Challenge methods tests
    @pytest.mark.asyncio
    async def test_create_challenge_upcoming(self, challenge_service, mock_db):
        # Arrange
        future_date = datetime.utcnow() + timedelta(days=1)
        end_date = future_date + timedelta(days=7)

        challenge_data = ChallengeCreate(
            challenge_name="Future Challenge",
            description="Upcoming test challenge",
            event_type=EventType.DATA_COLLECTION,
            task_type=TaskType.ANNOTATION,
            event_category=EventCategory.COMPETITION,
            start_date=future_date,
            end_date=end_date,
            reward=uuid.uuid4()

        )

        # Act
        result = await challenge_service.create_challenge(challenge_data)

        # Assert
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        assert result.status == ChallengeStatus.UPCOMING
        assert result.task_type == TaskType.TRANSCRIPTION  # Default for DATA_COLLECTION

    @pytest.mark.asyncio
    async def test_create_challenge_active(self, challenge_service, mock_db):
        # Arrange
        past_date = datetime.utcnow() - timedelta(days=1)
        future_date = datetime.utcnow() + timedelta(days=7)

        challenge_data = ChallengeCreate(
            challenge_name="Active Challenge",
            description="Active test challenge",
            event_type=EventType.DATA_COLLECTION,
            task_type=TaskType.ANNOTATION,
            event_category=EventCategory.COMPETITION,
            start_date=past_date,
            end_date=future_date,
            reward=uuid.uuid4()
        )

        # Act
        result = await challenge_service.create_challenge(challenge_data)

        # Assert
        assert result.status == ChallengeStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_challenge_completed(self, challenge_service, mock_db):
        # Arrange
        past_start = datetime.utcnow() - timedelta(days=10)
        past_end = datetime.utcnow() - timedelta(days=1)

        challenge_data = ChallengeCreate(
            challenge_name="Completed Challenge",
            description="Completed test challenge",
            event_type=EventType.DATA_COLLECTION,
            task_type=TaskType.ANNOTATION,
            event_category=EventCategory.COMPETITION,
            start_date=past_start,
            end_date=past_end,
            reward=uuid.uuid4()
        )

        # Act
        result = await challenge_service.create_challenge(challenge_data)

        # Assert
        assert result.status == ChallengeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_challenge(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.get_challenge(str(challengeid))

        # Assert
        mock_db.get.assert_awaited_once_with(Challenge, str(challengeid))
        assert result == mock_challenge

    @pytest.mark.asyncio
    async def test_update_challenge(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge

        update_data = ChallengeUpdate(
            challenge_name="Updated Challenge Name",
            description="Updated description"
        )

        # Act
        result = await challenge_service.update_challenge(str(challengeid), update_data)

        # Assert
        assert result == mock_challenge
        assert mock_challenge.challenge_name == "Updated Challenge Name"
        assert mock_challenge.description == "Updated description"
        mock_db.add.assert_called_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_challenge)

    @pytest.mark.asyncio
    async def test_update_challenge_recalculate_status_upcoming(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge
        future_date = datetime.utcnow() + timedelta(days=5)

        update_data = ChallengeUpdate(
            start_date=future_date
        )

        # Act
        result = await challenge_service.update_challenge(str(challengeid), update_data)

        # Assert
        assert result.status == ChallengeStatus.UPCOMING

    @pytest.mark.asyncio
    async def test_update_challenge_recalculate_status_completed(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge
        past_date = datetime.utcnow() - timedelta(days=5)

        update_data = ChallengeUpdate(
            end_date=past_date
        )

        # Act
        result = await challenge_service.update_challenge(str(challengeid), update_data)

        # Assert
        assert result.status == ChallengeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_challenge_not_found(self, challenge_service, mock_db):
        # Arrange
        mock_db.get.return_value = None

        update_data = ChallengeUpdate(
            challenge_name="Updated Challenge Name"
        )

        # Act
        result = await challenge_service.update_challenge("nonexistent", update_data)

        # Assert
        assert result is None
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_challenge_success(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_challenge.status = ChallengeStatus.UPCOMING
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.delete_challenge(str(challengeid))

        # Assert
        assert result is True
        mock_db.delete.assert_awaited_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_challenge_not_found(self, challenge_service, mock_db):
        # Arrange
        mock_db.get.return_value = None

        # Act
        result = await challenge_service.delete_challenge("nonexistent")

        # Assert
        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_challenge_active_error(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_challenge.status = ChallengeStatus.ACTIVE
        mock_db.get.return_value = mock_challenge

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete an active"):
            await challenge_service.delete_challenge(str(challengeid))

        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_challenges(self, challenge_service, mock_db):
        # Arrange
        mock_challenges = [MagicMock(spec=Challenge) for _ in range(3)]

        # Create mock for result.scalars().all()
        mock_scalar_result = MagicMock()
        mock_scalar_result.all.return_value = mock_challenges

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalar_result

        # Set it as the result of 'await mock_db.execute(...)'
        mock_db.execute.return_value = mock_execute_result

        query_params = GetChallenges(
            status=ChallengeStatus.ACTIVE,
            event_type=EventType.DATA_COLLECTION,
            is_public=True,
            skip=0,
            limit=10
        )

        # Act
        result = await challenge_service.list_challenges(query_params)

        # Assert
        mock_db.execute.assert_called_once()
        assert len(result) == 3
        assert result == mock_challenges

    @pytest.mark.asyncio
    async def test_publish_challenge(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_challenge.is_published = False
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.publish_challenge(str(challengeid))

        # Assert
        assert result.is_published is True
        mock_db.add.assert_called_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_challenge)

    @pytest.mark.asyncio
    async def test_publish_challenge_not_found(self, challenge_service, mock_db):
        # Arrange
        mock_db.get.return_value = None

        # Act
        result = await challenge_service.publish_challenge("nonexistent")

        # Assert
        assert result is None
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_unpublish_challenge(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_challenge.is_published = True
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.unpublish_challenge(str(challengeid))

        # Assert
        assert result.is_published is False
        mock_db.add.assert_called_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_challenge)

    @pytest.mark.asyncio
    async def test_update_challenge_status(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.update_challenge_status(str(challengeid), ChallengeStatus.COMPLETED)

        # Assert
        assert result.status == ChallengeStatus.COMPLETED
        mock_db.add.assert_called_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_challenge)

    # Challenge Participation methods tests
    @pytest.mark.asyncio
    async def test_join_challenge_success(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge
        mock_db.execute.return_value = None  # User not already participating

        participation_data = ChallengeParticipationCreate(
            event_id=challengeid,
            user_id=participationid
        )

        # Act
        participation, challenge = await challenge_service.join_challenge(participation_data)

        # Assert
        assert challenge.participant_count == 6  # Incremented from 5
        mock_db.add.call_count == 2  # Both participation and challenge
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.call_count == 2  # Both objects

    @pytest.mark.asyncio
    async def test_join_challenge_not_found(self, challenge_service, mock_db):
        # Arrange
        mock_db.get.return_value = None

        participation_data = ChallengeParticipationCreate(
            event_id=uuid.uuid4(),
            user_id=participationid
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Challenge not found"):
            await challenge_service.join_challenge(participation_data)

    @pytest.mark.asyncio
    async def test_join_challenge_already_participating(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_db.get.return_value = mock_challenge
        mock_db.execute.return_value = True  # User already participating

        participation_data = ChallengeParticipationCreate(
            event_id=challengeid,
            user_id=participationid
        )

        # Act & Assert
        with pytest.raises(ValueError, match="User is already participating"):
            await challenge_service.join_challenge(participation_data)

    @pytest.mark.asyncio
    async def test_leave_challenge_success(self, challenge_service, mock_db, mock_challenge, mock_participation):
        # Arrange
        mock_db.execute.return_value = mock_participation
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.leave_challenge(str(challengeid), str(participationid))

        # Assert
        assert result is True
        assert mock_challenge.participant_count == 4  # Decremented from 5
        mock_db.delete.assert_awaited_once_with(mock_participation)
        mock_db.add.assert_called_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_leave_challenge_not_participating(self, challenge_service, mock_db):
        # Arrange
        mock_db.execute.return_value = None

        # Act
        result = await challenge_service.leave_challenge(str(challengeid), str(participationid))

        # Assert
        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_leave_challenge_challenge_not_found(self, challenge_service, mock_db, mock_participation):
        # Arrange
        mock_db.execute.return_value = mock_participation
        mock_db.get.return_value = None

        # Act
        result = await challenge_service.leave_challenge(str(challengeid), str(participationid))

        # Assert
        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_challenge_participation(self, challenge_service, mock_db, mock_participation):
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_participation]
        mock_db.execute.return_value = mock_result

        # Act
        result = await challenge_service.get_challenge_participation(str(challengeid), str(participationid))

        # Assert
        assert result == mock_participation
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_challenge_participation_not_found(self, challenge_service, mock_db):
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Act
        result = await challenge_service.get_challenge_participation(str(challengeid), str(participationid))

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_participation_stats(self, challenge_service, mock_db, mock_participation):
        # Arrange
        # Mock the get_challenge_participation method
        with patch.object(challenge_service, 'get_challenge_participation', return_value=mock_participation):
            update_data = ChallengeParticipationUpdate(
                total_points=75,
                total_hours_speech=8
            )

            # Act
            result = await challenge_service.update_participation_stats(str(challengeid), str(participationid),
                                                                        update_data)

            # Assert
            assert result == mock_participation
            assert mock_participation.total_points == 75
            assert mock_participation.total_hours_speech == 8
            mock_db.add.assert_called_once_with(mock_participation)
            mock_db.commit.assert_awaited_once()
            mock_db.refresh.assert_awaited_once_with(mock_participation)

    @pytest.mark.asyncio
    async def test_update_participation_stats_not_found(self, challenge_service, mock_db):
        # Arrange
        # Mock the get_challenge_participation method
        with patch.object(challenge_service, 'get_challenge_participation', return_value=None):
            update_data = ChallengeParticipationUpdate(
                total_points=75
            )

            # Act
            result = await challenge_service.update_participation_stats(str(challengeid), str(participationid),
                                                                        update_data)

            # Assert
            assert result is None
            mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_challenge_participants(self, challenge_service, mock_db, mock_participation):
        # Arrange
        mock_participations = [mock_participation for _ in range(3)]

        # Properly mock the async DB result structure
        mock_scalar_result = MagicMock()
        mock_scalar_result.all.return_value = mock_participations

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalar_result

        mock_db.execute.return_value = mock_execute_result

        # Act
        result = await challenge_service.get_challenge_participants(str(challengeid))

        # Assert
        assert len(result) == 3
        assert result == mock_participations
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_challenges(self, challenge_service, mock_db, mock_participation):
        # Arrange
        mock_participations = [mock_participation for _ in range(2)]

        mock_scalar_result = MagicMock()
        mock_scalar_result.all.return_value = mock_participations

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalar_result

        mock_db.execute.return_value = mock_execute_result

        # Act
        result = await challenge_service.get_user_challenges(str(participationid))

        # Assert
        assert len(result) == 2
        assert result == mock_participations
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_challenge_contribution_count(self, challenge_service, mock_db, mock_challenge):
        # Arrange
        mock_challenge.contribution_count = 10
        mock_db.get.return_value = mock_challenge

        # Act
        result = await challenge_service.increment_challenge_contribution_count(str(challengeid))

        # Assert
        assert result.contribution_count == 11
        mock_db.add.assert_called_once_with(mock_challenge)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_challenge)

    @pytest.mark.asyncio
    async def test_increment_challenge_contribution_count_not_found(self, challenge_service, mock_db):
        # Arrange
        mock_db.get.return_value = None

        # Act
        result = await challenge_service.increment_challenge_contribution_count("nonexistent")

        # Assert
        assert result is None
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_challenge_leaderboard(self, challenge_service, mock_db):
        # Arrange
        mock_leaderboard_entries = [
            (MagicMock(spec=ChallengeParticipation, user_id="user1", total_points=100,
                       total_hours_speech=10, total_sentences_translated=200,
                       total_tokens_produced=2000, acceptance_rate=85.0),
             "username1", "User One"),
            (MagicMock(spec=ChallengeParticipation, user_id="user2", total_points=90,
                       total_hours_speech=9, total_sentences_translated=180,
                       total_tokens_produced=1800, acceptance_rate=80.0),
             "username2", "User Two")
        ]

        mock_db.execute.return_value = mock_leaderboard_entries

        # Act
        result = await challenge_service.get_challenge_leaderboard(str(challengeid))

        # Assert
        assert len(result) == 2
        assert result[0]["user_id"] == "user1"
        assert result[0]["username"] == "username1"
        assert result[0]["points"] == 100
        assert result[1]["user_id"] == "user2"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_challenge_statuses(self, challenge_service, mock_db):
        # Arrange
        # Create mock challenges that need status updates
        upcoming_challenge = MagicMock(spec=Challenge)
        upcoming_challenge.status = ChallengeStatus.UPCOMING
        upcoming_challenge.start_date = datetime.utcnow() - timedelta(hours=1)
        upcoming_challenge.end_date = datetime.utcnow() + timedelta(days=1)

        active_challenge = MagicMock(spec=Challenge)
        active_challenge.status = ChallengeStatus.ACTIVE
        active_challenge.end_date = datetime.utcnow() - timedelta(hours=1)

        # Correctly mocked results
        mock_db.execute.side_effect = [
            mock_scalar_result([upcoming_challenge]),
            mock_scalar_result([active_challenge])
        ]

        # Act
        count = await challenge_service.update_challenge_statuses()

        # Assert
        assert count == 2
        assert upcoming_challenge.status == ChallengeStatus.ACTIVE
        assert active_challenge.status == ChallengeStatus.COMPLETED
        assert mock_db.add.call_count == 2
        mock_db.commit.assert_awaited_once()
