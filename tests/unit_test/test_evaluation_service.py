import warnings
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from services.evaluation_service import EvaluationService
from models import ABTestVote, ABTestPair, ABTest

# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


# --- Fixtures ---
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def evaluation_service(mock_db):
    return EvaluationService(mock_db)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user_id = uuid.UUID('7f2f71ec-b9d2-49ef-a041-42a5cbbcbb1f')
    type(user).id = PropertyMock(return_value=user_id)
    return user


@pytest.fixture
def mock_ab_test():
    test = MagicMock()
    test.id = uuid.uuid4()
    test.is_complete = False
    test.contribution_type = "annotation"
    test.final_winner_id = None
    return test


# --- Tests for Evaluation Instance ---
@pytest.mark.asyncio
async def test_create_evaluation_instance(evaluation_service):
    # Setup test data
    sample_id = uuid.uuid4()
    contribution_type = "annotation"

    # Mock sample and instance
    mock_sample = MagicMock()
    mock_sample.evaluation_instance_id = None
    mock_instance = MagicMock()
    mock_instance.id = uuid.uuid4()

    # Mock contributions
    mock_contributions = [MagicMock(id=uuid.uuid4()) for _ in range(5)]

    # Set up query results
    sample_result = MagicMock()
    sample_result.scalars.return_value.first.return_value = mock_sample
    instance_result = MagicMock()
    instance_result.scalars.return_value.first.return_value = mock_instance

    # Mock database operations
    evaluation_service.db.execute = AsyncMock(side_effect=[sample_result, instance_result])

    with patch('services.contribution_service.ContributionManagementService') as MockContribService:
        # Setup contribution service
        contrib_service = MockContribService.return_value
        contrib_service.list_contributions = AsyncMock(return_value=mock_contributions)

        # Call method
        result = await evaluation_service.create_evaluation_instance(
            sample_id=sample_id,
            contribution_type=contribution_type,
            num_branches=3,
            max_depth=5
        )

        # Verify result
        assert result is mock_instance

        # Verify DB operations
        assert evaluation_service.db.add.call_count >= 1
        assert evaluation_service.db.commit.await_count >= 1


# @pytest.mark.asyncio
# async def test_get_evaluation_instance(evaluation_service):
#     instance_id = uuid.uuid4()
#     mock_instance = MagicMock()
#     mock_instance.complete = False  # Add necessary attributes
#
#     # Set up query result
#     query_result = MagicMock()
#     query_result.scalars.return_value.first.return_value = mock_instance
#     evaluation_service.db.execute = AsyncMock(return_value=query_result)
#
#     # Patch only the specific line causing the problem
#     with patch('services.evaluation_service.EvaluationInstance', autospec=True) as MockInstance:
#         # Set up the class attribute that gets used in selectinload
#         MockInstance.branches = "branches_attribute"
#
#         # Call the method
#         result = await evaluation_service.get_evaluation_instance(instance_id)
#
#     # Verify result
#     assert result is mock_instance
#     evaluation_service.db.execute.assert_awaited_once()


# --- Tests for Evaluation Steps ---
@pytest.mark.asyncio
async def test_submit_evaluation_step(evaluation_service):
    branch_id = uuid.uuid4()
    instance_id = uuid.uuid4()
    language_id = uuid.uuid4()
    user_id = uuid.uuid4()
    contribution_type = "annotation"

    # Mock branch
    mock_branch = MagicMock()
    mock_branch.id = branch_id
    mock_branch.is_complete = False
    mock_branch.current_contribution_id = uuid.uuid4()

    # Set up method mocks
    evaluation_service.get_branch = AsyncMock(return_value=mock_branch)

    # Mock settings to fix EVALUATION_POINTS error
    with patch('services.evaluation_service.settings') as mock_settings, \
            patch('services.contribution_service.ContributionManagementService') as MockContribService, \
            patch('services.language_service.LanguageService') as MockLanguageService, \
            patch('services.challenge_service.ChallengeService') as MockChallengeService:
        # Setup settings
        mock_settings.EVALUATION_POINTS = 10

        # Setup contribution service
        contrib_instance = MockContribService.return_value
        contrib_instance.upvote_contribution = AsyncMock()

        # Setup language service
        lang_instance = MockLanguageService.return_value
        lang_instance.user_language_repository = MagicMock()
        lang_instance.user_language_repository.update_language_stats = AsyncMock()

        # Setup challenge service
        challenge_instance = MockChallengeService.return_value
        challenge_instance.update_participation_stats = AsyncMock()

        # Call method
        result = await evaluation_service.submit_evaluation_step(
            branch_id=branch_id,
            instance_id=instance_id,
            language_id=language_id,
            user_id=user_id,
            contribution_type=contribution_type,
            decision=True
        )

        # Verify result
        assert result is True

        # Verify method calls
        contrib_instance.upvote_contribution.assert_awaited_once_with(
            contribution_id=mock_branch.current_contribution_id,
            contribution_type=contribution_type
        )

        lang_instance.user_language_repository.update_language_stats.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_evaluation_step(evaluation_service):
    step_id = uuid.uuid4()
    mock_step = MagicMock()

    # Set up query result
    query_result = MagicMock()
    query_result.scalars.return_value.first.return_value = mock_step
    evaluation_service.db.execute = AsyncMock(return_value=query_result)

    # Call method
    result = await evaluation_service.get_evaluation_step(step_id)

    # Verify result
    assert result is mock_step
    evaluation_service.db.execute.assert_awaited_once()


# @pytest.mark.asyncio
# async def test_get_branch(evaluation_service):
#     branch_id = uuid.uuid4()
#     mock_branch = MagicMock()
#     mock_branch.complete = False
#
#     # Set up query result
#     query_result = MagicMock()
#     query_result.scalars.return_value.first.return_value = mock_branch
#     evaluation_service.db.execute = AsyncMock(return_value=query_result)
#
#     # Patch only the specific line causing the problem
#     with patch('services.evaluation_service.EvaluationBranch', autospec=True) as MockBranch:
#         # Set up the class attribute that gets used in selectinload
#         MockBranch.steps = "steps_attribute"
#
#         # Call the method
#         result = await evaluation_service.get_branch(branch_id)
#
#     # Verify result
#     assert result is mock_branch
#     evaluation_service.db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_evaluation_step_to_user(evaluation_service):
    user_id = uuid.uuid4()
    proficiency_level = 2
    contribution_type = "annotation"

    # Mock branch and step
    mock_branch = MagicMock()
    mock_branch.id = uuid.uuid4()
    mock_branch.max_depth = 5

    mock_step = MagicMock()
    mock_step.id = uuid.uuid4()
    mock_step.head = True

    # Set up method mocks
    evaluation_service._get_candidate_branches_with_head_steps = AsyncMock(return_value=[mock_branch])
    evaluation_service._assign_or_create_step = AsyncMock(return_value=mock_step)

    # Call method
    result = await evaluation_service.assign_evaluation_step_to_user(
        user_id=user_id,
        proficiency_level=proficiency_level,
        contribution_type=contribution_type
    )

    # Verify result
    assert isinstance(result, list)
    assert len(result) == 1
    assert "task_type" in result[0]
    assert "branch_id" in result[0]
    assert "step_id" in result[0]

    # Verify method calls
    evaluation_service._get_candidate_branches_with_head_steps.assert_awaited_once()
    evaluation_service._assign_or_create_step.assert_awaited_once_with(user_id, mock_branch)


# --- Tests for A/B Testing ---
@pytest.mark.asyncio
async def test_init_ab_test(evaluation_service):
    instance_id = uuid.uuid4()
    contribution_type = "annotation"

    # Mock top contributions
    mock_contributions = [MagicMock(id=uuid.uuid4()) for _ in range(3)]

    # Mock existing test query
    test_query_result = MagicMock()
    test_query_result.scalars.return_value.first.return_value = None

    # Setup method mocks
    evaluation_service.select_top_contributions = AsyncMock(return_value=mock_contributions)
    evaluation_service.db.execute = AsyncMock(return_value=test_query_result)

    # Call method with patch for random.random to control pair creation
    with patch('random.random', return_value=0.7):
        result = await evaluation_service.init_ab_test(
            instance_id=instance_id,
            contribution_type=contribution_type
        )

        # Verify result
        assert result is not None

        # Verify DB operations
        assert evaluation_service.db.add.call_count >= 1
        assert evaluation_service.db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_get_ab_test(evaluation_service):
    ab_test_id = uuid.uuid4()
    mock_test = MagicMock()

    # Set up query result
    query_result = MagicMock()
    query_result.scalars.return_value.first.return_value = mock_test
    evaluation_service.db.execute = AsyncMock(return_value=query_result)

    # Call method
    result = await evaluation_service.get_ab_test(ab_test_id)

    # Verify result
    assert result is mock_test
    evaluation_service.db.execute.assert_awaited_once()


@pytest.mark.parametrize("is_complete,expected_keys", [
    (True, ["error", "final_winners"]),
    (False, ["ab_test_id", "pair_id", "vote_id", "stage_number", "option_a", "option_b", "a_shown_first"])
])
@pytest.mark.asyncio
async def test_assign_ab_test_to_user(evaluation_service, mock_user, mock_ab_test, is_complete, expected_keys):
    # Setup test data
    user_id = mock_user.id
    test_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    contrib_a_id = uuid.uuid4()
    contrib_b_id = uuid.uuid4()
    vote_id = uuid.uuid4()

    # Configure mock_ab_test for this test case
    mock_ab_test.is_complete = is_complete
    mock_ab_test.final_winner_id = uuid.uuid4() if is_complete else None
    mock_ab_test.current_stage = 1

    # Set up method mocks
    evaluation_service.get_ab_test = AsyncMock(return_value=mock_ab_test)

    if not is_complete:
        # Mock pair and votes
        mock_pair = MagicMock()
        mock_pair.id = pair_id
        mock_pair.contribution_a_id = contrib_a_id
        mock_pair.contribution_b_id = contrib_b_id
        mock_pair.min_votes_required = 3
        mock_pair.votes = []

        # Set up pair query
        pair_result = MagicMock()
        pair_scalars = MagicMock()
        pair_scalars.all.return_value = [mock_pair]
        pair_result.scalars.return_value = pair_scalars

        # Mock contributions
        mock_contrib_a = MagicMock()
        mock_contrib_a.text = "Test A"
        mock_contrib_b = MagicMock()
        mock_contrib_b.text = "Test B"

        # Set up contribution management service mock
        with patch('services.contribution_service.ContributionManagementService') as MockContribService:
            contrib_service = MockContribService.return_value
            contrib_service.get_contribution = AsyncMock(side_effect=[mock_contrib_a, mock_contrib_b])

            # Set up vote mock
            mock_vote = MagicMock()
            mock_vote.id = vote_id
            mock_vote.user_id = user_id
            mock_vote.a_shown_first = True

            evaluation_service.db.execute = AsyncMock(return_value=pair_result)

            # Call method with patched ABTestVote
            with patch('services.evaluation_service.ABTestVote') as MockABTestVote:
                MockABTestVote.return_value = mock_vote

                result = await evaluation_service.assign_ab_test_to_user(
                    ab_test_id=test_id,
                    user_id=user_id,
                    proficiency_level=1
                )

                # Verify correct ABTestVote construction
                MockABTestVote.assert_called_once()
                call_kwargs = MockABTestVote.call_args[1]
                assert call_kwargs['user_id'] == user_id
                assert call_kwargs['pair_id'] == pair_id
    else:
        # For completed test, just check error message
        result = await evaluation_service.assign_ab_test_to_user(
            ab_test_id=test_id,
            user_id=user_id,
            proficiency_level=1
        )

    # Verify result structure based on test case
    assert isinstance(result, dict)
    for key in expected_keys:
        assert key in result


@pytest.mark.asyncio
async def test_submit_ab_test_result(evaluation_service):
    # Setup test data
    vote_id = uuid.uuid4()
    selected_contribution_id = uuid.uuid4()
    pair_id = uuid.uuid4()
    test_id = uuid.uuid4()
    language_id = uuid.uuid4()
    challenge_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Mock vote
    mock_vote = MagicMock()
    mock_vote.id = vote_id
    mock_vote.user_id = user_id
    mock_vote.selected_contribution_id = None

    # Mock pair
    mock_pair = MagicMock()
    mock_pair.id = pair_id
    mock_pair.contribution_a_id = selected_contribution_id
    mock_pair.contribution_b_id = uuid.uuid4()
    mock_pair.min_votes_required = 3
    mock_pair.stage_number = 1

    # Mock AB test
    mock_test = MagicMock()
    mock_test.id = test_id
    mock_test.is_complete = False

    # Connect mocks
    mock_vote.pair = mock_pair
    mock_pair.ab_test = mock_test

    # Set up vote query
    vote_result = MagicMock()
    vote_scalars = MagicMock()
    vote_scalars.first.return_value = mock_vote
    vote_result.scalars.return_value = vote_scalars

    # Set up votes count query
    votes_result = MagicMock()
    votes_scalars = MagicMock()
    votes_scalars.all.return_value = [mock_vote]
    votes_result.scalars.return_value = votes_scalars

    # Set up database execution
    evaluation_service.db.execute = AsyncMock(side_effect=[vote_result, votes_result])
    evaluation_service.db.commit = AsyncMock()  # Create a fresh mock for each test

    # Mock settings to fix points error
    with patch('services.evaluation_service.settings') as mock_settings, \
            patch('services.challenge_service.ChallengeService') as MockChallengeService, \
            patch('services.language_service.LanguageService') as MockLanguageService:
        # Setup settings
        mock_settings.POINTS_PER_AB_TEST_VOTE = 5

        # Setup challenge service
        challenge_service = MockChallengeService.return_value
        challenge_service.update_participation_stats = AsyncMock()

        # Setup language service
        language_service = MockLanguageService.return_value
        language_service.user_language_repository = MagicMock()
        language_service.user_language_repository.update_language_stats = AsyncMock()

        # Call method
        result = await evaluation_service.submit_ab_test_result(
            vote_id=vote_id,
            selected_contribution_id=selected_contribution_id,
            challenge_id=challenge_id,
            language_id=language_id
        )

        # Verify result
        assert "success" in result
        assert result["success"] is True
        assert "vote_id" in result
        assert "can_advance" in result

        # Verify vote was updated
        assert mock_vote.selected_contribution_id == selected_contribution_id
        assert mock_vote.vote_submitted_at is not None

        # Verify stats were updated
        challenge_service.update_participation_stats.assert_awaited_once()
        language_service.user_language_repository.update_language_stats.assert_awaited_once()

        # Verify DB operations - allow any number of commits
        assert evaluation_service.db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_advance_ab_test(evaluation_service):
    # Setup test data
    test_id = uuid.uuid4()
    contribution_type = "annotation"

    # Create a valid UUID for the winner
    winner_id = uuid.uuid4()

    # Mock AB test
    mock_test = MagicMock()
    mock_test.id = test_id
    mock_test.current_stage = 1
    mock_test.target_winner_count = 1
    mock_test.min_stage_depth = 1
    mock_test.min_votes_threshold = 3
    mock_test.is_complete = False
    mock_test.contribution_type = contribution_type

    # Mock pairs
    mock_pair = MagicMock()
    mock_pair.id = uuid.uuid4()

    # Mock votes with a valid UUID
    mock_vote = MagicMock()
    mock_vote.selected_contribution_id = winner_id

    # Set up pair query result
    pairs_result = MagicMock()
    pairs_scalars = MagicMock()
    pairs_scalars.all.return_value = [mock_pair]
    pairs_result.scalars.return_value = pairs_scalars

    # Set up votes query result
    votes_result = MagicMock()
    votes_scalars = MagicMock()
    votes_scalars.all.return_value = [mock_vote]
    votes_result.scalars.return_value = votes_scalars

    # Set up update result for _mark_contribution_as_winner
    update_result = MagicMock()

    # Set up method mocks with enough mock results for all db.execute calls
    evaluation_service.get_ab_test = AsyncMock(return_value=mock_test)
    evaluation_service.db.execute = AsyncMock(side_effect=[pairs_result, votes_result, update_result])

    # Call method with patched random.shuffle to make tests deterministic
    with patch('random.shuffle'):
        result = await evaluation_service.advance_ab_test(
            ab_test_id=test_id,
            contribution_type=contribution_type
        )

    # Verify result
    assert result["ab_test_id"] == mock_test.id
    assert "is_complete" in result

    # Verify db.execute was called the expected number of times
    assert evaluation_service.db.execute.await_count == 3


@pytest.mark.asyncio
async def test_finalize_ab_test(evaluation_service):
    # Setup test data
    test_id = uuid.uuid4()

    # Create valid UUIDs for pair contributions
    contribution_a_id = uuid.uuid4()
    contribution_b_id = uuid.uuid4()

    # Use string representation for the AB test data
    contribution_a_str = str(contribution_a_id)
    contribution_b_str = str(contribution_b_id)

    # Mock AB test with proper UUID strings in the data
    mock_test = MagicMock()
    mock_test.id = test_id
    mock_test.is_complete = False
    mock_test.ab_test_data = {
        "stages": [{"complete": False, "results": {}, "pairs": [(contribution_a_str, contribution_b_str)]}],
        "stage_winners": [],
        "contribution_type": "annotation"  # Add the required contribution type
    }

    # Set up method mocks
    evaluation_service.get_ab_test = AsyncMock(return_value=mock_test)
    evaluation_service._mark_contribution_as_winner = AsyncMock()
    evaluation_service.db.commit = AsyncMock()

    # Call method
    result = await evaluation_service.finalize_ab_test(test_id)

    # Verify result
    assert isinstance(result, dict)
    assert result["ab_test_id"] == mock_test.id
    assert "is_complete" in result
    assert result["is_complete"] is True

    # Verify that _mark_contribution_as_winner was called with the correct UUID
    evaluation_service._mark_contribution_as_winner.assert_awaited_once_with(
        contribution_a_id, "annotation"
    )


@pytest.mark.asyncio
async def test_select_top_contributions(evaluation_service):
    # Setup test data
    instance_id = uuid.uuid4()
    contribution_type = "annotation"

    # Mock sample
    mock_sample = MagicMock()
    mock_sample.words = {"test": 5, "word": 3}
    mock_sample.evaluation_instance = MagicMock(is_complete=True)

    # Mock contributions
    mock_contributions = []
    for i in range(5):
        contrib = MagicMock()
        contrib.id = uuid.uuid4()
        contrib.text = f"test word {i}"
        contrib.upvotes = i
        mock_contributions.append(contrib)

    # Set up sample query
    sample_result = MagicMock()
    sample_result.scalars.return_value.first.return_value = mock_sample

    # Mock ContributionManagementService
    with patch('services.contribution_service.ContributionManagementService') as MockContribService:
        contrib_service = MockContribService.return_value
        contrib_service.list_contributions = AsyncMock(return_value=mock_contributions)

        # Set up database execution
        evaluation_service.db.execute = AsyncMock(return_value=sample_result)

        # Call method
        result = await evaluation_service.select_top_contributions(
            instance_id=instance_id,
            contribution_type=contribution_type,
            limit=3
        )

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 3

        # Top contributions should have highest scores
        assert result[0].upvotes == 4  # Highest upvotes
