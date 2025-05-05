import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from models.challenge import (
    Challenge, ChallengeParticipation,
    ChallengeStatus, EventType, TaskType, EventCategory
)
from schemas.challenge import (
    ChallengeCreate, ChallengeUpdate, ChallengeParticipationCreate,
    ParticipationUpdate, GetChallenges, ChallengeRulesAdd
)
from services.challenge_service import ChallengeService


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def challenge_service(mock_db):
    return ChallengeService(mock_db)


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
    challenge.status = ChallengeStatus.UPCOMING
    challenge.is_public = True
    challenge.is_published = False
    challenge.reward_id = uuid.uuid4()
    challenge.language_id = uuid.uuid4()
    challenge.completion_percent = 100
    challenge.required_fields = []
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
    participation.contribution_count = 2
    participation.accepted_contributions = 1
    participation.evaluation_count = 1
    participation.accepted_evaluations = 1
    return participation


@pytest.mark.asyncio
async def test_create_challenge(challenge_service, mock_db):
    challenge_data = ChallengeCreate(
        challenge_name="Test Challenge",
        description="Test Desc",
        language_id=uuid.uuid4(),
    )
    result = await challenge_service.create_challenge(challenge_data)
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()
    assert result.challenge_name == "Test Challenge"
    assert result.status == ChallengeStatus.UPCOMING


@pytest.mark.asyncio
async def test_add_challenge_rules_success(challenge_service, mock_db, mock_challenge):
    with patch.object(challenge_service, "get_challenge", return_value=mock_challenge):
        challenge_service.rule_repository.add_rules = AsyncMock()
        data = ChallengeRulesAdd(challenge_id=challengeid, rules=[{
            "rule_title": "test",
            "rule_description": "test",
            "is_required": True
        }])
        result = await challenge_service.add_challenge_rules(data)
        challenge_service.rule_repository.add_rules.assert_awaited_once()
        assert result == mock_challenge


@pytest.mark.asyncio
async def test_add_challenge_rules_challenge_not_found(challenge_service, mock_db):
    mock_db.get.return_value = None
    data = ChallengeRulesAdd(challenge_id=challengeid, rules=[{
        "rule_title": "test",
        "rule_description": "test",
        "is_required": True
    }])
    with pytest.raises(HTTPException) as exc:
        await challenge_service.add_challenge_rules(data)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_challenge_rules_published(challenge_service, mock_db, mock_challenge):
    mock_challenge.is_published = True
    with patch.object(challenge_service, "get_challenge", return_value=mock_challenge):
        data = ChallengeRulesAdd(challenge_id=challengeid, rules=[{
            "rule_title": "test",
            "rule_description": "test",
            "is_required": True
        }])
        with pytest.raises(HTTPException) as exc:
            await challenge_service.add_challenge_rules(data)
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_progress_updates_fields(challenge_service, mock_db, mock_challenge):
    with patch.object(challenge_service, "get_challenge", return_value=mock_challenge):
        update_data = ChallengeUpdate(description="New Desc")
        result = await challenge_service.update_progress(challengeid, update_data)
    assert result.description == "New Desc"
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(mock_challenge)


@pytest.mark.asyncio
async def test_update_progress_challenge_not_found(challenge_service, mock_db):
    with patch.object(challenge_service, "get_challenge",
                      side_effect=HTTPException(status_code=404, detail="Challenge not found")):
        update_data = ChallengeUpdate(description="New Desc")
        with pytest.raises(HTTPException) as exc:
            await challenge_service.update_progress(uuid.uuid4(), update_data)
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_challenge_found(challenge_service, mock_db, mock_challenge):
    mock_db.get.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=mock_challenge))))
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.get_challenge(challengeid)
    assert result == mock_challenge


@pytest.mark.asyncio
async def test_get_challenge_not_found(challenge_service, mock_db):
    mock_db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await challenge_service.get_challenge(uuid.uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_is_published_true(challenge_service, mock_db, mock_challenge):
    mock_challenge.is_published = True
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.is_published(challengeid)
    assert result is True


@pytest.mark.asyncio
async def test_is_published_false(challenge_service, mock_db, mock_challenge):
    mock_challenge.is_published = False
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.is_published(challengeid)
    assert result is False


@pytest.mark.asyncio
async def test_update_challenge_success(challenge_service, mock_db, mock_challenge):
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        update = ChallengeUpdate(description="desc")
        result = await challenge_service.update_challenge(challengeid, update)
    assert result == mock_challenge


@pytest.mark.asyncio
async def test_update_challenge_not_found(challenge_service, mock_db):
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=None):
        update = ChallengeUpdate(description="desc")
        result = await challenge_service.update_challenge(uuid.uuid4(), update)
    assert result is None

@pytest.mark.asyncio
async def test_delete_challenge_success(challenge_service, mock_db, mock_challenge):
    mock_challenge.status = ChallengeStatus.UPCOMING
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.delete_challenge(challengeid)
    assert result is True
    mock_db.delete.assert_awaited_once_with(mock_challenge)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_challenge_active_error(challenge_service, mock_db, mock_challenge):
    mock_challenge.status = ChallengeStatus.ACTIVE
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        with pytest.raises(ValueError):
            await challenge_service.delete_challenge(challengeid)


@pytest.mark.asyncio
async def test_list_challenges(challenge_service, mock_db):
    mock_challenges = [MagicMock(spec=Challenge) for _ in range(2)]
    mock_scalar_result = MagicMock()
    mock_scalar_result.all.return_value = mock_challenges
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalar_result
    mock_db.execute.return_value = mock_execute_result
    query_params = GetChallenges(status=ChallengeStatus.UPCOMING, skip=0, limit=10)
    result = await challenge_service.list_challenges(query_params)
    assert result == mock_challenges


@pytest.mark.asyncio
async def test_publish_challenge_success(challenge_service, mock_db, mock_challenge):
    mock_challenge.completion_percent = 100
    mock_challenge.is_published = False
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.publish_challenge(challengeid)
    assert result.is_published is True
    mock_db.add.assert_called_once_with(mock_challenge)
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(mock_challenge)


@pytest.mark.asyncio
async def test_publish_challenge_incomplete(challenge_service, mock_db, mock_challenge):
    mock_challenge.completion_percent = 80
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        with pytest.raises(ValueError):
            await challenge_service.publish_challenge(challengeid)


@pytest.mark.asyncio
async def test_unpublish_challenge_success(challenge_service, mock_db, mock_challenge):
    mock_challenge.status = ChallengeStatus.UPCOMING
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.unpublish_challenge(challengeid)
    assert result.is_published is False


@pytest.mark.asyncio
async def test_unpublish_challenge_active_error(challenge_service, mock_db, mock_challenge):
    mock_challenge.status = ChallengeStatus.ACTIVE
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        with pytest.raises(ValueError):
            await challenge_service.unpublish_challenge(challengeid)


@pytest.mark.asyncio
async def test_update_challenge_status_success(challenge_service, mock_db, mock_challenge):
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.update_challenge_status(challengeid, ChallengeStatus.ACTIVE)
    assert result.status == ChallengeStatus.ACTIVE


@pytest.mark.asyncio
async def test_join_challenge_success(challenge_service, mock_db, mock_challenge):
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        # Create a mock result object with scalar_one_or_none returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        data = ChallengeParticipationCreate(event_id=challengeid, user_id=participationid)
        participation, challenge = await challenge_service.join_challenge(data)
    assert challenge.participant_count == 6
    mock_db.add.assert_any_call(participation)
    mock_db.add.assert_any_call(challenge)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_join_challenge_already_participating(challenge_service, mock_db, mock_challenge):
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        data = ChallengeParticipationCreate(event_id=challengeid, user_id=participationid)
        with pytest.raises(ValueError):
            await challenge_service.join_challenge(data)


@pytest.mark.asyncio
async def test_leave_challenge_success(challenge_service, mock_db, mock_challenge, mock_participation):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_participation
    mock_db.execute = AsyncMock(return_value=mock_result)
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.leave_challenge(challengeid, participationid)
    assert result is True
    assert mock_challenge.participant_count == 4
    mock_db.delete.assert_awaited_once_with(mock_participation)


@pytest.mark.asyncio
async def test_leave_challenge_not_participating(challenge_service, mock_db, mock_challenge):
    # Properly mock the async DB result structure
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=mock_challenge):
        result = await challenge_service.leave_challenge(challengeid, participationid)
    assert result is False


@pytest.mark.asyncio
async def test_leave_challenge_challenge_not_found(challenge_service, mock_db, mock_participation):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_participation
    mock_db.execute = AsyncMock(return_value=mock_result)
    with patch("services.challenge_service.ChallengeService.get_challenge", return_value=None):
        result = await challenge_service.leave_challenge(challengeid, participationid)
    assert result is False




@pytest.mark.asyncio
async def test_get_challenge_participation_found(challenge_service, mock_db, mock_participation):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_participation]
    mock_db.execute.return_value = mock_result
    result = await challenge_service.get_challenge_participation(challengeid, participationid)
    assert result == mock_participation


@pytest.mark.asyncio
async def test_get_challenge_participation_not_found(challenge_service, mock_db):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    result = await challenge_service.get_challenge_participation(challengeid, participationid)
    assert result is None


@pytest.mark.asyncio
async def test_update_participation_stats_success(challenge_service, mock_db, mock_participation):
    with patch.object(challenge_service, 'get_challenge_participation', return_value=mock_participation):
        update_data = ParticipationUpdate(total_points=75, total_hours_speech=8)
        result = await challenge_service.update_participation_stats(challengeid, participationid, update_data)
    assert result == mock_participation


@pytest.mark.asyncio
async def test_update_participation_stats_not_found(challenge_service, mock_db):
    with patch.object(challenge_service, 'get_challenge_participation', return_value=None):
        update_data = ParticipationUpdate(total_points=75)
        result = await challenge_service.update_participation_stats(challengeid, participationid, update_data)
    assert result is None


@pytest.mark.asyncio
async def test_get_challenge_participants(challenge_service, mock_db, mock_participation):
    mock_participations = [mock_participation for _ in range(3)]
    mock_scalar_result = MagicMock()
    mock_scalar_result.all.return_value = mock_participations
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalar_result
    mock_db.execute.return_value = mock_execute_result
    result = await challenge_service.get_challenge_participants(challengeid)
    assert result == mock_participations


@pytest.mark.asyncio
async def test_get_user_challenges(challenge_service, mock_db, mock_participation):
    mock_participations = [mock_participation for _ in range(2)]
    mock_scalar_result = MagicMock()
    mock_scalar_result.all.return_value = mock_participations
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalar_result
    mock_db.execute.return_value = mock_execute_result
    result = await challenge_service.get_user_challenges(participationid)
    assert result == mock_participations


@pytest.mark.asyncio
async def test_get_challenge_leaderboard(challenge_service, mock_db):
    mock_leaderboard_entries = [
        (MagicMock(spec=ChallengeParticipation, user_id="user1", total_points=100, total_hours_speech=10,
                   total_sentences_translated=200, total_tokens_produced=2000, acceptance_rate=85.0), "username1",
         "User One"),
        (MagicMock(spec=ChallengeParticipation, user_id="user2", total_points=90, total_hours_speech=9,
                   total_sentences_translated=180, total_tokens_produced=1800, acceptance_rate=80.0), "username2",
         "User Two")
    ]
    mock_db.execute.return_value = mock_leaderboard_entries
    result = await challenge_service.get_challenge_leaderboard(challengeid)
    assert len(result) == 2
    assert result[0]["user_id"] == "user1"
    assert result[1]["user_id"] == "user2"


@pytest.mark.asyncio
async def test_update_challenge_statuses(challenge_service, mock_db, mock_challenge):
    upcoming = MagicMock(spec=Challenge)
    upcoming.status = ChallengeStatus.UPCOMING
    upcoming.start_date = datetime.utcnow() - timedelta(hours=1)
    upcoming.end_date = datetime.utcnow() + timedelta(days=1)
    active = MagicMock(spec=Challenge)
    active.status = ChallengeStatus.ACTIVE
    active.end_date = datetime.utcnow() - timedelta(hours=1)

    def mock_scalar_result(val):
        mock_scalar = MagicMock()
        mock_scalar.all.return_value = val
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalar
        return mock_result

    mock_db.execute.side_effect = [mock_scalar_result([upcoming]), mock_scalar_result([active])]
    count = await challenge_service.update_challenge_statuses()
    assert count == 2
    assert upcoming.status == ChallengeStatus.ACTIVE
    assert active.status == ChallengeStatus.COMPLETED
    mock_db.commit.assert_awaited_once()
