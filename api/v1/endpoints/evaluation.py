from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from pydantic import UUID4

from database import get_session
from models.user import User
from schemas.evaluation import (
    EvaluationStepSubmit,
    ABTestVoteSubmit
)
from services.evaluation_service import EvaluationService
from api.v1.deps import get_current_active_user, get_current_superuser

router = APIRouter()


# Dependencies
def get_evaluation_service(db: AsyncSession = Depends(get_session)):
    return EvaluationService(db)


# ======== EVALUATION STEPS ========

@router.post("/step/{branch_id}/submit", summary="Submit an evaluation step")
async def submit_evaluation_step(
        branch_id: UUID4 = Path(..., description="The branch ID"),
        instance_id: UUID4 = Query(..., description="The evaluation instance ID"),
        language_id: UUID4 = Query(..., description="The language ID"),
        contribution_type: str = Query(..., description="Type of contribution"),
        data: EvaluationStepSubmit = None,
        service: EvaluationService = Depends(get_evaluation_service),
        current_user: User = Depends(get_current_active_user)
):
    """Submit a decision for an evaluation step"""
    try:
        result = await service.submit_evaluation_step(
            branch_id=branch_id,
            instance_id=instance_id,
            language_id=language_id,
            user_id=current_user.id,
            contribution_type=contribution_type,
            eval_decision=data.eval_decision if data else None,
            correction_id=data.correction_id if data else None,
            run_abtest=data.run_abtest if data else False
        )
        return {"success": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assign", summary="Assign evaluation steps to a user")
async def assign_evaluation_steps(
        user_proficiency: int = Query(1, ge=1, le=10, description="User proficiency level (1-10)"),
        contribution_type: str = Query(..., description="Type of contribution to evaluate"),
        challenge_id: Optional[UUID4] = Query(None, description="Optional challenge ID filter"),
        language_id: Optional[UUID4] = Query(None, description="Optional language ID filter"),
        num_steps: int = Query(1, ge=1, le=10, description="Number of steps to assign"),
        service: EvaluationService = Depends(get_evaluation_service),
        current_user: User = Depends(get_current_active_user)
):
    """Assign evaluation steps to the current user"""
    try:
        result = await service.assign_evaluation_step_to_user(
            user_id=current_user.id,
            proficiency_level=user_proficiency,
            contribution_type=contribution_type,
            challenge_id=challenge_id,
            language_id=language_id,
            num_steps=num_steps
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ======== A/B TESTING ========
@router.get("/abtest/assign", summary="Assign an A/B test pair to a user")
async def assign_ab_test_to_user(
        ab_test_id: Optional[UUID4] = Query(None, description="Optional specific A/B test ID"),
        user_proficiency: int = Query(1, ge=1, le=10, description="User proficiency level (1-10)"),
        service: EvaluationService = Depends(get_evaluation_service),
        current_user: User = Depends(get_current_active_user)
):
    """Assign an A/B test comparison to the current user"""
    try:
        return await service.assign_ab_test_to_user(
            user_id=current_user.id,
            proficiency_level=user_proficiency,
            ab_test_id=ab_test_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/abtest/vote/{pair_id}", summary="Cast a vote on an A/B test pair")
async def cast_vote(
        pair_id: UUID4 = Path(..., description="The A/B test pair ID"),
        data: ABTestVoteSubmit = None,
        service: EvaluationService = Depends(get_evaluation_service),
        current_user: User = Depends(get_current_active_user)
):
    """Cast a vote on an A/B test pair, supporting one or two selected contributions (ties)"""
    if not data:
        raise HTTPException(status_code=400, detail="Vote data is required")

    try:
        return await service.cast_vote(
            pair_id=pair_id,
            user_id=current_user.id,
            selected_contribution_ids=data.selected_contribution_ids,
            contribution_type=data.contribution_type,
            language_id=data.language_id,
            challenge_id=data.challenge_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# store
# ======== EVALUATION INSTANCES ========

# @router.post("/instance/", summary="Create a new evaluation instance")
# async def create_evaluation_instance(
#         data: EvaluationInstanceCreate,
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_superuser)
# ):
#     """Create a new evaluation instance for a sample"""
#     try:
#         instance = await service.create_evaluation_instance(
#             sample_id=data.sample_id,
#             contribution_type=data.contribution_type,
#             num_branches=data.num_branches
#         )
#         return instance
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
#
# @router.get("/instance/{instance_id}", summary="Get an evaluation instance")
# async def get_evaluation_instance(
#         instance_id: UUID4 = Path(..., description="The evaluation instance ID"),
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_active_user)
# ):
#     """Get details of an evaluation instance"""
#     try:
#         return await service.get_evaluation_instance(instance_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#
# @router.get("/step/{step_id}", summary="Get an evaluation step")
# async def get_evaluation_step(
#         step_id: UUID4 = Path(..., description="The step ID"),
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_active_user)
# ):
#     """Get details of an evaluation step"""
#     try:
#         return await service.get_evaluation_step(step_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#
#
# @router.get("/branch/{branch_id}", summary="Get an evaluation branch")
# async def get_branch(
#         branch_id: UUID4 = Path(..., description="The branch ID"),
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_active_user)
# ):
#     """Get details of an evaluation branch"""
#     try:
#         return await service.get_branch(branch_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))
#
# ======== A/B TESTING ========

# @router.post("/abtest/{instance_id}/init", summary="Initialize A/B testing for an evaluation instance")
# async def init_ab_test(
#         instance_id: UUID4 = Path(..., description="The evaluation instance ID"),
#         contribution_type: str = Query(..., description="Type of contribution"),
#         winners: int = Query(1, ge=1, description="Number of winners to select"),
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_superuser)
# ):
#     """Initialize A/B testing for a completed evaluation instance"""
#     try:
#         return await service.init_ab_test(
#             instance_id=instance_id,
#             contribution_type=contribution_type,
#             winners=winners
#         )
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @router.get("/abtest/{ab_test_id}", summary="Get A/B test details")
# async def get_ab_test(
#         ab_test_id: UUID4 = Path(..., description="The A/B test ID"),
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_active_user)
# ):
#     """Get details of an A/B test"""
#     try:
#         return await service.get_ab_test(ab_test_id)
#     except ValueError as e:
#         raise HTTPException(status_code=404, detail=str(e))

# @router.post("/abtest/{ab_test_id}/finalize", summary="Finalize an A/B test")
# async def finalize_ab_test(
#         ab_test_id: UUID4 = Path(..., description="The A/B test ID"),
#         service: EvaluationService = Depends(get_evaluation_service),
#         current_user: User = Depends(get_current_superuser)
# ):
#     """Finalize an A/B test and determine the overall winner"""
#     try:
#         return await service.finalize_ab_test(ab_test_id)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
