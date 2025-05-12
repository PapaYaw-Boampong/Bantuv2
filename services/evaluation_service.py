import math
import uuid
from typing import Dict, List, Optional, Union, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
import random
from core.config import settings
from models import (
    EvaluationInstance,
    EvaluationBranch,
    EvaluationStep,
    ABTest,
    AnnotationContribution,
    TranscriptionContribution,
    TranslationContribution,
    TranslationSample,
    TranscriptionSample,
    AnnotationSample,
    ABTestPair,
    ABTestVote,
)

import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Print to console
        logging.FileHandler('evaluation_service.log')  # Save to file
    ]
)

# Create a logger specific to this module
logger = logging.getLogger("evaluation_service")


from schemas.contribution import (
    ContributionFilter,
)

from schemas.challenge import (
    ParticipationUpdate,
)

# Helper Methods
from utils.eval_service_utils import (
    filter_user_participated,
    prioritize_branches,
    is_expired,
)


class EvaluationService:
    """
    Service responsible for managing the progressive validation of
    user-generated contributions through branch-based evaluation and A/B testing.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_type = {
            "annotation": (AnnotationContribution, AnnotationSample),
            "transcription": (TranscriptionContribution, TranscriptionSample),
            "translation": (TranslationContribution, TranslationSample)
        }

    async def _get_models(self, contribution_type: str) -> Tuple[Any, Any]:
        """Get the appropriate contribution and evaluation record models based on type"""
        if contribution_type not in self.task_type:
            raise ValueError(f"Invalid contribution type: {contribution_type}")
        return self.task_type[contribution_type]

    # =========== Creating Evaluation Instances ==========
    async def create_evaluation_instance(
            self,
            sample_id: uuid.UUID,
            contribution_type: str,
            num_branches: int = 2,
    ) -> EvaluationInstance:
        """
        Initialize an evaluation instance for a given sample.

        Args:
            sample_id: The ID of the sample to evaluate
            contribution_type: "annotation", "transcription", or "translation"
            num_branches: Number of parallel evaluation branches

        Returns:
            The created EvaluationInstance
        """
        try:
            # Define pipe depths based on contribution type
            pipe_depths = {
                "annotation": settings.ANNOTATION_PIPE_DEPTH,
                "transcription": settings.TRANSCRIPTION_PIPE_DEPTH,
                "translation": settings.TRANSLATION_PIPE_DEPTH
            }
            max_depth = pipe_depths.get(contribution_type, 3)

            # Validate the contribution type
            if contribution_type not in self.task_type:
                raise ValueError(f"Invalid contribution type: {contribution_type}")

            # Create the evaluation instance
            instance_data = {
                "num_branches": num_branches,
                "is_complete": False,
                "num_completed_branches": 0
            }

            instance = EvaluationInstance(**instance_data)
            self.db.add(instance)
            
            try:
                await self.db.commit()
                await self.db.refresh(instance)
            except Exception as commit_error:
                print(f"Error committing evaluation instance: {str(commit_error)}")
                await self.db.rollback()
                raise

            # Link the sample to the instance
            _, sample_model = await self._get_models(contribution_type)

            stmt = select(sample_model).where(sample_model.id == sample_id)
            sample = (await self.db.execute(stmt)).scalars().first()

            if not sample:
                raise ValueError(f"No sample found with ID {sample_id} for {contribution_type}")

            # Ensure sample isn't already linked to an evaluation instance
            if sample.evaluation_instance_id:
                raise ValueError(f"Sample with ID {sample_id} is already linked to an evaluation instance")

            sample.evaluation_instance_id = instance.id
            self.db.add(sample)

            from services.contribution_service import ContributionManagementService
            contribution_management_service = ContributionManagementService(self.db)

            # Get contributions from ContributionManagementService
            filters = ContributionFilter(
                sample_id=sample_id,
                flagged=False
            )

            contributions = await contribution_management_service.list_contributions(
                contribution_type=contribution_type,
                filters=filters,
            )

            if len(contributions) < num_branches:
                raise ValueError("Not enough contributions to create the requested number of branches")

            contribution_ids = [str(c.id) for c in contributions]

            # Create the branches with initial contributions
            for i in range(min(num_branches, len(contribution_ids))):
                branch = EvaluationBranch(
                    instance_id=instance.id,
                    current_contribution_id=contribution_ids[i],
                    depth=1,
                    max_depth=max_depth,
                    is_complete=False
                )
                self.db.add(branch)

                # Create initial evaluation step
                step = EvaluationStep(
                    branch_id=branch.id,
                    b_contribution_id=contribution_ids[i],
                    is_complete=False,
                    head=True,
                    step_number=1,
                )
                self.db.add(step)

            try:
                await self.db.commit()
            except Exception as commit_error:
                print(f"Error committing branches and steps: {str(commit_error)}")
                await self.db.rollback()
                raise

            # Refresh instance to get created branches
            try:
                stmt = select(EvaluationInstance).where(EvaluationInstance.id == instance.id).options(
                    selectinload(EvaluationInstance.evaluation_branches).selectinload(EvaluationBranch.evaluation_steps)
                )
                result = await self.db.execute(stmt)
                instance = result.scalars().first()
            except Exception as refresh_error:
                print(f"Error refreshing instance: {str(refresh_error)}")
                # Continue anyway with the already created instance

            return instance
            
        except Exception as e:
            print(f"Error in create_evaluation_instance: {str(e)}")
            try:
                await self.db.rollback()
            except:
                pass
            raise ValueError(f"Error creating evaluation instance: {str(e)}")

    # =========== Managing Evaluation Steps ==========
    async def submit_evaluation_step(
            self,
            branch_id: uuid.UUID,
            instance_id: uuid.UUID,
            language_id: uuid.UUID,
            user_id: uuid.UUID,
            contribution_type: str,
            eval_decision: Optional[bool] = None,
            correction_id: Optional[uuid.UUID] = None,
            run_abtest: bool = False,
    ) -> bool:
        """
        Submit and progress an evaluation step in a branch.
        Returns:
            True if submission was successful

        """
        if eval_decision is None:
            # Treat as a skipped evaluation — no stat increment or contribution change
            pass

        # 1. Get the branch and check for completion
        branch = await self.get_branch(branch_id)

        # 2. Handle contribution resolution
        from services.contribution_service import ContributionManagementService
        cms = ContributionManagementService(self.db)

        # 3. Get the result of the possible abtest
        eval_step = await self.get_evaluation_step(branch_id)
        if eval_step.abtest_decision == "a":
            await cms.unpackPoints(eval_step.b_contribution_id, contribution_type)
            advancing_contribution = eval_step.a_contribution_id
        elif eval_step.abtest_decision == "b":
            await cms.unpackPoints(eval_step.a_contribution_id, contribution_type)
            advancing_contribution = eval_step.b_contribution_id
        else:
            raise ValueError("Invalid A/B test decision in evaluation Service")

        # 4. check if the advancing contribution is accepted or correction is made - if so then run abtest in next step
        if eval_decision is False:
            # Use correction (assumes it's already created & valid)
            if not correction_id:
                raise ValueError(
                    "Correction ID must be provided if contribution is not upvoted")  # will possibly remove for skipped

            # Init abtest
            run_abtest = True
        else:
            await cms.update_ancestors(advancing_contribution, contribution_type, user_id)

        # 3. Mark current head step as complete and not head
        await self.db.execute(
            update(EvaluationStep)
            .where(
                and_(
                    EvaluationStep.branch_id == branch_id,
                    EvaluationStep.head == True
                )
            )
            .values(
                head=False,
                is_complete=True,
                evaluation_decision=eval_decision,
                abtest_decision=eval_step.abtest_decision,
                next_alt_contribution_id=correction_id
            )
        )

        # Prepare next step or finish instance
        if branch.is_complete:

            # 4. Upack points for the advancing contribution and possibly last correction

            if correction_id:
                await cms.unpackPoints(correction_id, contribution_type)

            await cms.unpackPoints(advancing_contribution, contribution_type)

            # 5. Check if instance is complete

            await self._check_instance_completion(instance_id)

        else:

            # 6. Increment branch depth and create next evaluation step

            branch.depth += 1
            next_step = EvaluationStep(
                branch_id=branch.id,
                instance_id=instance_id,
                b_contribution_id=advancing_contribution,
                a_contribution_id=correction_id,
                head=True,
                is_complete=False,
                step_number=branch.depth + 1,
                run_abtest=run_abtest,

            )
            self.db.add(next_step)

        # Update evaluator stats
        from services.language_service import LanguageService
        language_service = LanguageService(self.db)
        from services.challenge_service import ChallengeService

        eval_stats = ParticipationUpdate(
            is_evaluation=True
        )

        # Update challenge participation stats
        if branch.event_id:
            challenge_service = ChallengeService(self.db)
            await challenge_service.update_participation_stats(
                event_id=branch.event_id,
                user_id=user_id,
                stats_data=eval_stats,
            )
        await language_service.user_language_repository.update_language_stats(
            user_id=user_id,
            language_id=language_id,
            stats_data=eval_stats,
        )

        # Commit everything
        await self.db.commit()
        return True

    async def get_evaluation_step(self, step_id: uuid.UUID) -> EvaluationStep:
        """Get an evaluation step by ID"""
        try:
            condition = EvaluationStep.id == step_id
            stmt = select(EvaluationStep).where(condition)
            result = await self.db.execute(stmt)
            step: EvaluationStep | None = result.scalars().first()

            # Check if step exists
            if not step:
                raise ValueError(f"Step with ID {step_id} not found")

            return step
        except Exception as e:
            print(f"Error in get_evaluation_step: {str(e)}")
            raise ValueError(f"Error retrieving evaluation step: {str(e)}")

    async def _check_instance_completion(self, instance_id: uuid.UUID) -> bool:
        """
        Check if all branches in an instance are complete, and if so,
        mark the instance as complete and potentially set up A/B testing.

        Returns:
            True if instance is now complete, False otherwise

        """
        # Get the instance and its branches
        instance = await self.get_evaluation_instance(instance_id)

        if not instance:
            raise ValueError(f"Evaluation instance {instance_id} not found")

        # Check if all branches are complete
        all_complete = all(branch.complete for branch in instance.branches)

        if all_complete and not instance.is_complete:
            instance.is_complete = True
            await self.db.commit()

            # Evaluate Users for their contributions
            # assigns points to users based on

            # If A/B test is required, initialize it
            if instance.ab_test:
                await self.init_ab_test(
                    instance_id=instance.id,
                    contribution_type=instance.task_type
                )

            return True

        return instance.is_complete

    async def get_evaluation_instance(self, instance_id: uuid.UUID) -> EvaluationInstance:
        """Get an evaluation instance by ID"""
        stmt = (
            select(EvaluationInstance)
            .where(EvaluationInstance.id == instance_id)
            .options(selectinload(EvaluationInstance.branches))
        )

        result = await self.db.execute(stmt)
        instance = result.scalars().first()

        if not instance:
            raise ValueError(f"Evaluation instance {instance_id} not found")

        return instance

    async def get_branch(self, branch_id: uuid.UUID) -> EvaluationBranch:
        """Get an evaluation branch by ID"""
        stmt = (
            select(EvaluationBranch)
            .where(EvaluationBranch.id == branch_id)  # type: ignore
            .options(selectinload(EvaluationBranch.steps))
        )

        result = await self.db.execute(stmt)
        branch: EvaluationBranch | None = result.scalars().first()
        # Check if branch exists
        if not branch:
            raise ValueError(f"Branch with ID {branch_id} not found")
        if branch.complete:
            raise ValueError(f"Branch {branch_id} is already complete")

        return branch

    # =========== Evaluations ==========
    async def assign_evaluation_step_to_user(
            self,
            user_id: uuid.UUID,
            proficiency_level: int,
            contribution_type: str,
            challenge_id: Optional[uuid.UUID] = None,
            language_id: Optional[uuid.UUID] = None,
            num_steps: int = 1,
    ) -> List[dict]:
        """
        Assign evaluation steps to a user based on their proficiency level.
        Prioritizes existing branches before creating new evaluation instances.
        """
        try:
            assignments = []
            steps_assigned = 0
            
            # Try to get and assign existing branches first
            try:
                # Get candidate branches with head steps
                branches = await self._get_candidate_branches_with_head_steps()
                
                # Filter out branches where user has already participated
                filtered_branches = filter_user_participated(branches, user_id)
                
                # Prioritize branches based on user's proficiency
                prioritized = prioritize_branches(filtered_branches, proficiency_level)

                # 1. Assign from existing prioritized branches
                for branch in prioritized:
                    if steps_assigned >= num_steps:
                        break

                    # Assign or create step for this branch
                    try:
                        step = await self._assign_or_create_step(user_id, branch)
                    
                        # Get basic step data
                        step_data = {
                            "step_id": str(step.id),
                            "branch_id": str(branch.id),
                            "head": step.head,
                            "assigned_at": step.assigned_at
                        }
                        
                        # Get contribution data in a separate try block
                        try:
                            step_with_contributions = await self.get_evaluation_step_with_contributions(
                                step_id=step.id,
                                contribution_type=contribution_type
                            )
                            step_data["contributions"] = step_with_contributions.get("contributions", {})
                        except Exception as contrib_error:
                            print(f"Error getting contributions for step {step.id}: {str(contrib_error)}")
                            step_data["contributions"] = {}
                            step_data["contribution_error"] = str(contrib_error)

                        assignments.append({
                            "task_type": "evaluation_step",
                            "branch_id": str(branch.id),
                            "depth": len(branch.evaluation_steps) if hasattr(branch, 'evaluation_steps') else 1,
                            "max_depth": branch.max_depth,
                            "step_id": str(step.id),
                            "head": step.head,
                            "note": "Assigned from existing branch",
                            "step_data": step_data
                        })
                        steps_assigned += 1
                    except Exception as e:
                        print(f"Error assigning step for branch {branch.id}: {str(e)}")
                        continue
            except Exception as branch_error:
                print(f"Error assigning from existing branches: {str(branch_error)}")
                # Continue to try creating new instances

            # 2. If not enough steps assigned, create new evaluation instances
            if steps_assigned < num_steps:
                remaining = num_steps - steps_assigned

                try:
                    # Get the appropriate model for the contribution type
                    _, model = self.task_type[contribution_type]
                    
                    # Import and instantiate SampleDataService
                    from services.sample_data_service import SampleDataService
                    sample_data_service = SampleDataService(self.db)
                    
                    # Get sample IDs for evaluation
                    sample_ids = await sample_data_service.find_samples_for_user(
                        user_id=user_id,
                        contribution_type=contribution_type,
                        language_id=language_id,
                        limit=remaining,
                    )



                    if not sample_ids:
                        if not assignments:  # If we haven't assigned anything yet
                            raise ValueError("No samples available for evaluation")
                        return assignments
                        
                    # Create new evaluation instances for each sample
                    for sample_id in sample_ids:
                        try:
                            # Create a new evaluation instance with fewer branches
                            instance = await self.create_evaluation_instance(
                                sample_id=sample_id,
                                contribution_type=contribution_type,
                                num_branches=2,  # Use minimum branches to speed up creation
                            )
                            logger.info(f"sample ids{instance}")
                            logger.debug(f"sample ids{contribution_type}")
                            
                            # Access the first branch and its first evaluation step
                            if hasattr(instance, 'branches'):
                                branch = instance.branches[0]
                                step = branch.steps[0] if hasattr(branch, 'steps') else branch.evaluation_steps[0]
                            else:
                                branch = instance.evaluation_branches[0]
                                step = branch.evaluation_steps[0]
                            
                            # Assign step to user
                            step.user_id = user_id
                            step.assigned_at = datetime.utcnow()
                            
                            # Commit changes to database
                            try:
                                await self.db.commit()
                                await self.db.refresh(step)
                            except Exception as commit_error:
                                print(f"Error committing step assignment: {str(commit_error)}")
                                await self.db.rollback()
                                continue

                            # Create basic step data
                            step_data = {
                                "step_id": str(step.id),
                                "branch_id": str(branch.id),
                                "head": step.head,
                                "assigned_at": step.assigned_at
                            }
                            
                            # Get contribution data in a separate try block
                            try:
                                step_with_contributions = await self.get_evaluation_step_with_contributions(
                                    step_id=step.id,
                                    contribution_type=contribution_type
                                )
                                step_data["contributions"] = step_with_contributions.get("contributions", {})
                            except Exception as contrib_error:
                                print(f"Error getting contributions for step {step.id}: {str(contrib_error)}")
                                step_data["contributions"] = {}
                                step_data["contribution_error"] = str(contrib_error)

                            assignments.append({
                                "task_type": "evaluation_step",
                                "branch_id": str(branch.id),
                                "depth": 1,
                                "max_depth": branch.max_depth,
                                "step_id": str(step.id),
                                "head": step.head if hasattr(step, 'head') else True,
                                "note": "New evaluation instance created",
                                "step_data": step_data
                            })

                            steps_assigned += 1
                            if steps_assigned >= num_steps:
                                break
                        except Exception as e:
                            print(f"Error creating evaluation instance for sample {sample_id}: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Error getting samples: {str(e)}")
                    if not assignments:  # If we haven't assigned anything yet
                        raise ValueError(f"Error getting samples: {str(e)}")

            return assignments
            
        except Exception as e:
            print(f"Error in assign_evaluation_step_to_user: {str(e)}")
            raise ValueError(f"Error assigning evaluation steps: {str(e)}")

    async def get_evaluation_step_with_contributions(
            self,
            step_id: uuid.UUID,
            contribution_type: str
    ) -> Dict[str, Any]:
        """
        Get an evaluation step by ID and fetch all associated contributions

        Args:
            step_id: The ID of the evaluation step
            contribution_type: The type of contribution (annotation, transcription, translation)

        Returns:
            Dict with step data and all associated contribution objects
        """
        try:
            # Get the evaluation step
            step = await self.get_evaluation_step(step_id)

            # Initialize contribution service to fetch contributions
            from services.contribution_service import ContributionManagementService
            contribution_service = ContributionManagementService(self.db)

            # Dictionary to store contribution objects
            contributions = {}

            # Fetch the best contribution (b_contribution)
            if step.b_contribution_id:
                try:
                    b_contribution = await contribution_service.get_contribution(
                        step.b_contribution_id,
                        contribution_type
                    )
                    contributions["b_contribution"] = b_contribution
                except Exception as e:
                    print(f"Error fetching b_contribution: {str(e)}")
                    contributions["b_contribution"] = None

            # Fetch the alternative contribution (a_contribution) if present
            if step.a_contribution_id:
                try:
                    a_contribution = await contribution_service.get_contribution(
                        step.a_contribution_id,
                        contribution_type
                    )
                    contributions["a_contribution"] = a_contribution
                except Exception as e:
                    print(f"Error fetching a_contribution: {str(e)}")
                    contributions["a_contribution"] = None

            # Fetch the next alternative contribution if present
            if step.next_alt_contribution_id:
                try:
                    next_alt_contribution = await contribution_service.get_contribution(
                        step.next_alt_contribution_id,
                        contribution_type
                    )
                    contributions["next_alt_contribution"] = next_alt_contribution
                except Exception as e:
                    print(f"Error fetching next_alt_contribution: {str(e)}")
                    contributions["next_alt_contribution"] = None

            # Build the response object with minimal database access
            step_data = {
                "step_id": str(step.id),
                "branch_id": str(step.branch_id),
                "step_number": step.step_number if hasattr(step, 'step_number') else 1,
                "run_ab_test": step.run_ab_test if hasattr(step, 'run_ab_test') else False,
                "abtest_decision": step.abtest_decision if hasattr(step, 'abtest_decision') else None,
                "assigned_at": step.assigned_at,
                "contributions": contributions
            }

            return step_data
            
        except Exception as e:
            print(f"Error in get_evaluation_step_with_contributions: {str(e)}")
            # Return a minimal response with error information
            return {
                "step_id": str(step_id),
                "error": str(e),
                "contributions": {}
            }

    async def _get_candidate_branches_with_head_steps(
            self
    ) -> List[EvaluationBranch]:
        try:
            stmt = (
                select(EvaluationBranch)
                .join(EvaluationInstance)
                .join(EvaluationStep)
                .options(
                    selectinload(EvaluationBranch.evaluation_steps),
                    selectinload(EvaluationBranch.evaluation_instance),
                )
                .where(EvaluationBranch.is_complete == False)
                .where(EvaluationInstance.is_complete == False)
                .where(
                    and_(
                        EvaluationStep.head == True,
                        EvaluationStep.is_complete == False,
                        or_(
                            EvaluationStep.user_id.is_(None),
                            EvaluationStep.assigned_at < datetime.utcnow() - timedelta(minutes=45)
                        )
                    )
                )
            )
            result = await self.db.execute(stmt)
            branches: List[EvaluationBranch] = result.scalars().unique().all()
            return branches
        except Exception as e:
            print(f"Error in _get_candidate_branches_with_head_steps: {str(e)}")
            # Return an empty list instead of raising an error
            return []

    async def _assign_or_create_step(
            self,
            user_id: uuid.UUID,
            branch: EvaluationBranch
    ) -> EvaluationStep:
        try:
            head_step = next((s for s in branch.evaluation_steps if s.head), None)

            # Reassign if unassigned or expired
            if head_step and (head_step.user_id is None or is_expired(head_step)):
                head_step.user_id = user_id
                head_step.assigned_at = datetime.utcnow()
                try:
                    await self.db.commit()
                    await self.db.refresh(head_step)
                except Exception as commit_error:
                    print(f"Error committing head_step assignment: {str(commit_error)}")
                    # Try to roll back if possible
                    try:
                        await self.db.rollback()
                    except:
                        pass
                    raise
                return head_step

            # Otherwise, create a new step
            new_step = EvaluationStep(
                branch_id=branch.id,
                user_id=user_id,
                head=False,
                is_complete=False,
                is_approved=False,
                assigned_at=datetime.utcnow()
            )
            try:
                self.db.add(new_step)
                await self.db.commit()
                await self.db.refresh(new_step)
            except Exception as commit_error:
                print(f"Error committing new step creation: {str(commit_error)}")
                # Try to roll back if possible
                try:
                    await self.db.rollback()
                except:
                    pass
                raise
            return new_step
        except Exception as e:
            print(f"Error in _assign_or_create_step: {str(e)}")
            raise ValueError(f"Error assigning step: {str(e)}")

    async def select_top_contributions(
            self,
            instance_id: uuid.UUID,
            contribution_type: str
    ) -> List[Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]]:
        """
        Select top contributions by retrieving the final contributions from each branch's
        head evaluation step (b_contribution_id and next_alt_contribution_id if present).
        """
        from services.contribution_service import ContributionManagementService
        contribution_management_service = ContributionManagementService(self.db)

        # Get evaluation instance with all branches
        stmt = (
            select(EvaluationInstance)
            .where(EvaluationInstance.id == instance_id)
            .options(
                selectinload(EvaluationInstance.evaluation_branches)
                .selectinload(EvaluationBranch.evaluation_steps)
            )
        )

        instance = (await self.db.execute(stmt)).scalars().first()

        if not instance:
            raise ValueError(f"Evaluation instance {instance_id} not found")

        if not instance.is_complete:
            raise ValueError(f"Evaluation instance is not complete")

        # Collect contribution IDs from head evaluation steps
        contribution_ids = set()

        for branch in instance.evaluation_branches:
            # Find head evaluation step for each branch
            head_step = next((step for step in branch.evaluation_steps
                              if step.is_complete and step.head), None)

            if head_step:
                # Add B contribution (best so far)
                if head_step.b_contribution_id:
                    contribution_ids.add(head_step.b_contribution_id)

                # Add alternative contribution if available
                if head_step.next_alt_contribution_id:
                    contribution_ids.add(head_step.next_alt_contribution_id)

        if not contribution_ids:
            return []

        # Get contribution objects
        top_contributions = []
        contribution_model, _ = await self._get_models(contribution_type)

        for contribution_id in list(contribution_ids):
            contribution = await contribution_management_service.get_contribution(
                contribution_id=contribution_id,
                contribution_type=contribution_type
            )
            if contribution:
                top_contributions.append(contribution)

        return top_contributions

    # =========== A/B Testing ==========
    async def init_ab_test(
            self,
            instance_id: uuid.UUID,
            contribution_type: str,
            winners: int = 1
    ) -> ABTest:
        """
        Initialize A/B testing for an evaluation instance.
        Creates pairwise comparisons of the top contributions in a tournament structure.

        Args:
            instance_id: ID of the evaluation instance
            contribution_type: Type of contribution (annotation, transcription, translation)
            winners: Number of winners to select (default=1)
            min_votes_threshold: Minimum votes needed for statistical significance

        Returns:
            The created ABTest instance
        """

        # Check if an A/B test already exists
        stmt = select(ABTest).where(ABTest.instance_id == instance_id)
        existing_test: ABTest = (await self.db.execute(stmt)).scalars().first()

        if existing_test:
            return existing_test

        # Get top contributions for this instance
        top_contributions = await self.select_top_contributions(
            instance_id=instance_id,
            contribution_type=contribution_type
        )

        if len(top_contributions) < 2:
            raise ValueError("Need at least 2 contributions for A/B testing")

        test_depth = round(math.log(len(top_contributions), 2), 0) + 1 + settings.AB_TEST_MARGIN

        # Create the AB test with enhanced metadata
        ab_test = ABTest(
            instance_id=instance_id,
            target_winner_count=winners,
            stage_count=1,  # Start with stage 1
            current_stage=1,
            test_depth=test_depth,
        )

        self.db.add(ab_test)
        await self.db.commit()
        await self.db.refresh(ab_test)

        # Create pairs for the first stage of the tournament
        contribution_ids = [str(c.id) for c in top_contributions]

        # Create pairs for the tournament
        pairs = []
        for i in range(0, len(contribution_ids) - 1, 2):
            if i + 1 < len(contribution_ids):
                # Create a pair with randomized order

                if random.random() > 0.5:
                    pairs.append((contribution_ids[i], contribution_ids[i + 1]))
                else:
                    pairs.append((contribution_ids[i + 1], contribution_ids[i]))

        # Handle odd number of contributions
        if len(contribution_ids) % 2 != 0 and len(contribution_ids) > 0:
            # Last contribution gets bye to the next round
            last_id = contribution_ids[-1]

            # Choose a random index except the last one
            random_index = random.randint(0, len(contribution_ids) - 2)
            random_id = contribution_ids[random_index]

            # Randomize the order of the pair for FE Orientation
            if random.random() > 0.5:
                pairs.append((last_id, random_id))
            else:
                pairs.append((random_id, last_id))

        # Create ABTestPair records for each pair
        for contribution_a_id, contribution_b_id in pairs:
            pair = ABTestPair(
                ab_test_id=ab_test.id,
                stage_number=1,  # First stage
                contribution_a_id=uuid.UUID(contribution_a_id),
                contribution_b_id=uuid.UUID(contribution_b_id)
            )
            self.db.add(pair)

        await self.db.commit()
        await self.db.refresh(ab_test)

        return ab_test

    async def cast_vote(
            self,
            pair_id: uuid.UUID,
            user_id: uuid.UUID,
            selected_contribution_ids: List[uuid.UUID],
            contribution_type: str,
            language_id: Optional[uuid.UUID],
            challenge_id: Optional[uuid.UUID] = None,

    ) -> dict:
        """
        Cast a vote for a specific A/B test pair.
        """
        # Check if the pair exists
        stmt = select(ABTestPair).where(ABTestPair.id == pair_id)
        pair = (await self.db.execute(stmt)).scalars().first()

        if not pair:
            raise ValueError(f"Pair with ID {pair_id} not found")

        # Check if the vote already exists
        stmt = select(ABTestVote).where(
            and_(
                ABTestVote.pair_id == pair_id,
                ABTestVote.user_id == user_id
            )
        )
        existing_vote = (await self.db.execute(stmt)).scalars().first()

        if existing_vote:
            raise ValueError(f"Vote already exists for user {user_id} on pair {pair_id}")

        # Validate selected contributions are part of this pair
        valid_ids = [pair.contribution_a_id, pair.contribution_b_id]
        for contribution_id in selected_contribution_ids:
            if contribution_id not in valid_ids:
                raise ValueError(f"Selected contribution {contribution_id} is not part of this pair")

        # Create the vote
        vote = ABTestVote(
            pair_id=pair.id,
            user_id=user_id,
            selected_contribution_ids=selected_contribution_ids,
            vote_submitted_at=datetime.utcnow()
        )
        self.db.add(vote)
        await self.db.commit()
        await self.db.refresh(vote)

        result = await self.submit_ab_test_result(
            vote_id=vote.id,
            selected_contribution_ids=selected_contribution_ids,
            challenge_id=challenge_id,
            language_id=language_id,

        )

        if result["success"]:
            if result["can_advance"]:
                try:
                    advance_result = await self.advance_ab_test(pair.ab_test_id, contribution_type)

                    result["advance"] = advance_result

                except Exception as e:

                    raise ValueError(f"Failed to advance A/B test: {e}")

        return result

    async def advance_ab_test(self, ab_test_id: uuid.UUID, contribution_type: str):
        """
        Advance an A/B test to the next stage.
        """
        ab_test = await self.get_ab_test(ab_test_id)
        if not ab_test:
            raise ValueError(f"No ABTest found with ID {ab_test_id}")

        # Find the current stage number
        current_stage = ab_test.current_stage

        # Get all pairs for this stage
        stmt = select(ABTestPair).where(
            and_(
                ABTestPair.ab_test_id == ab_test.id,
                ABTestPair.stage_number == current_stage
            )
        )
        pairs = (await self.db.execute(stmt)).scalars().all()

        # Tally votes for each pair and determine winners
        advancing_contributions = []
        for pair in pairs:
            # Get votes for this pair
            vote_stmt = select(ABTestVote).where(ABTestVote.pair_id == pair.id)
            votes = (await self.db.execute(vote_stmt)).scalars().first()

            winners = []
            winners.extend(votes.selected_contribution_ids)

        # Remove duplicates while preserving order
        seen = set()
        unique_advancing = []
        for cid in advancing_contributions:
            if cid not in seen:
                unique_advancing.append(cid)
                seen.add(cid)
        advancing_contributions = unique_advancing

        # If only one winner or target_winner_count reached, finalize
        if ab_test.current_stage >= ab_test.min_stage_depth:
            ab_test.is_complete = True
            ab_test.completed_at = datetime.now(timezone.utc)
            ab_test.final_winner_ids = [uuid.UUID(contribution_id) for contribution_id in advancing_contributions]

            await self._mark_contribution_as_winner(uuid.UUID(advancing_contributions[0]), contribution_type)
            await self.db.commit()
            await self.db.refresh(ab_test)
            return {
                "ab_test_id": ab_test.id,
                "is_complete": True,
                "final_winners": advancing_contributions
            }
        # Otherwise, create next stage pairs
        next_stage = current_stage + 1
        random.shuffle(advancing_contributions)
        new_pairs = []
        num_adv = len(advancing_contributions)
        i = 0
        while i < num_adv - 1:
            new_pairs.append((advancing_contributions[i], advancing_contributions[i + 1]))
            i += 2
        if num_adv % 2 != 0 and num_adv > 1:
            last_idx = num_adv - 1
            possible_indices = list(range(num_adv - 1))
            random_idx = random.choice(possible_indices)
            pair = (advancing_contributions[last_idx], advancing_contributions[random_idx])
            # Optionally randomize order
            if random.random() > 0.5:
                pair = (pair[1], pair[0])
            new_pairs.append(pair)
        for contribution_a_id, contribution_b_id in new_pairs:
            pair = ABTestPair(
                ab_test_id=ab_test.id,
                stage_number=next_stage,
                contribution_a_id=uuid.UUID(contribution_a_id),
                contribution_b_id=uuid.UUID(contribution_b_id),
                min_votes_required=ab_test.min_votes_threshold,
                metrics={}
            )
            self.db.add(pair)
        ab_test.current_stage = next_stage
        ab_test.test_depth = next_stage
        await self.db.commit()
        await self.db.refresh(ab_test)
        return {
            "ab_test_id": ab_test.id,
            "is_complete": False,
            "current_stage": next_stage,
            "all_pairs_complete": True,
            "advancing_contributions": len(advancing_contributions)
        }

    async def get_ab_test(self, ab_test_id: uuid.UUID) -> ABTest:
        """Get an A/B test by ID"""
        stmt = select(ABTest).where(ABTest.id == ab_test_id)
        result = await self.db.execute(stmt)
        ab_test: ABTest = result.scalars().first()

        if not ab_test:
            raise ValueError(f"A/B test with ID {ab_test_id} not found")

        return ab_test

    async def get_random_ab_test(self) -> ABTest:
        """Get a random incomplete and open A/B test"""
        stmt = (
            select(ABTest)
            .where(ABTest.is_complete == False)  # Only incomplete tests
            .order_by(func.random())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        ab_test: ABTest = result.scalars().first()

        if not ab_test:
            raise ValueError("No incomplete A/B tests found")

        return ab_test

    async def get_ab_test_for_instance(self, instance_id: uuid.UUID) -> Optional[ABTest]:
        """Get the A/B test for an evaluation instance"""
        stmt = select(ABTest).where(ABTest.instance_id == instance_id)
        result = await self.db.execute(stmt)
        ab_test = result.scalars().first()

        return ab_test

    async def assign_ab_test_to_user(
            self,
            user_id: uuid.UUID,
            proficiency_level: int = 1,
            ab_test_id: uuid.UUID = None
    ) -> Dict[str, Any]:
        """
        Assign an A/B test comparison to a user with randomization.

        Args:
            ab_test_id: ID of A/B test
            user_id: ID of user to assign to
            proficiency_level: User's proficiency level (1-10)

        Returns:
            Dict with the pair of contributions to compare and evaluation criteria
        """
        # Get the A/B test
        if ab_test_id is None:
            ab_test = await self.get_random_ab_test()
        else:
            ab_test = await self.get_ab_test(ab_test_id)

        if ab_test.is_complete:
            return {
                "error": "A/B test is already complete",
                "final_winners": ab_test.final_winner_id
            }

        # Get pairs from the current stage that haven't been completed
        current_stage = ab_test.current_stage
        stmt = select(ABTestPair).where(
            and_(
                ABTestPair.ab_test_id == ab_test_id,
                ABTestPair.stage_number == current_stage,
                ABTestPair.is_complete == False
            )
        ).options(selectinload(ABTestPair.votes))

        pairs = (await self.db.execute(stmt)).scalars().all()
        pairs = list(pairs)

        if not pairs:
            return {
                "error": "No active pairs found in the current stage",
                "current_stage": current_stage
            }

        # Find a pair that hasn't been voted on by this user
        # Shuffle the pairs to randomize assignment
        random.shuffle(pairs)

        from datetime import datetime, timezone

        TTE_SECONDS = getattr(settings, "TTE", 72000)  # Default to 1 hour if not set
        for pair in pairs:
            # Check if this user has already voted on this pair
            user_voted = any(vote.user_id == user_id for vote in pair.votes)
            if user_voted:
                continue

            # Check for stale votes (assigned but not completed, and TTE expired)
            now = datetime.now(timezone.utc)
            stale_vote = None
            for vote in pair.votes:
                if (
                        vote.selected_contribution_id is None and
                        (now - vote.vote_assigned_at).total_seconds() > TTE_SECONDS
                ):
                    stale_vote = vote
                    break

            from services.contribution_service import ContributionManagementService
            contribution_management_service = ContributionManagementService(self.db)

            # Get the contribution content
            contribution_a = await contribution_management_service.get_contribution(
                pair.contribution_a_id,
                ab_test.contribution_type
            )
            contribution_b = await contribution_management_service.get_contribution(
                pair.contribution_b_id,
                ab_test.contribution_type
            )
            if not contribution_a or not contribution_b:
                continue

            def get_content(c):
                if hasattr(c, "text"):
                    return c.text
                return str(c.id)

            # If there is a stale vote, reassign it
            if stale_vote:
                stale_vote.user_id = user_id
                stale_vote.vote_assigned_at = now
                stale_vote.user_proficiency = proficiency_level
                self.db.add(stale_vote)
                await self.db.commit()
                await self.db.refresh(stale_vote)
                vote = stale_vote
                a_shown_first = vote.a_shown_first
            else:
                # Randomize the presentation order (50% chance A shown first)
                a_shown_first = random.random() > 0.5
                vote = ABTestVote(
                    pair_id=pair.id,
                    user_id=user_id,
                    selected_contribution_id=None,  # Will be set when submitted
                    vote_assigned_at=now,
                    user_proficiency=proficiency_level,
                    a_shown_first=a_shown_first
                )
                self.db.add(vote)
                await self.db.commit()
                await self.db.refresh(vote)

            first_contribution = {
                "id": str(pair.contribution_a_id if a_shown_first else pair.contribution_b_id),
                "content": get_content(contribution_a if a_shown_first else contribution_b)
            }
            second_contribution = {
                "id": str(pair.contribution_b_id if a_shown_first else pair.contribution_a_id),
                "content": get_content(contribution_b if a_shown_first else contribution_a)
            }
            return {
                "ab_test_id": str(ab_test_id),
                "pair_id": str(pair.id),
                "vote_id": str(vote.id),
                "stage_number": current_stage,
                "option_a": first_contribution,
                "option_b": second_contribution,
                "a_shown_first": a_shown_first  # For tracking presentation bias
            }

        # If we get here, the user has voted on all available pairs
        return {
            "error": "No available pairs for voting",
            "suggestion": "Try advancing the test to the next stage if all votes are in"
        }

    async def submit_ab_test_result(
            self,
            vote_id: uuid.UUID,
            selected_contribution_ids: List[uuid.UUID],
            language_id: Optional[uuid.UUID],
            challenge_id: Optional[uuid.UUID] = None,

    ) -> Dict[str, Any]:
        """
        Submit a user's selection for an A/B test comparison with multi-criteria evaluation.

        Args:
            vote_id: ID of the vote record
            selected_contribution_ids: ID of the selected contribution
            challenge_id: Optional ID of the challenge
            language_id: Optional ID of the language
        Returns:
            Dict with submission status
        """
        # Get the vote record
        stmt = select(ABTestVote).where(ABTestVote.id == vote_id).options(
            selectinload(ABTestVote.pair).joinedload(ABTestPair.ab_test)
        )
        vote_result = await self.db.execute(stmt)
        vote = vote_result.scalars().first()

        if not vote:
            return {
                "error": "Vote not found"
            }

        # Get the pair and test
        pair = vote.pair
        ab_test = pair.ab_test

        if ab_test.is_complete:
            return {
                "error": "A/B test is already complete",
                "final_winners": ab_test.final_winner_id
            }

        # Mark this pair as complete and set the winner
        pair.is_complete = True
        pair.winner_ids.append(selected_contribution_ids)
        self.db.add(pair)

        eval_stats = ParticipationUpdate(
            is_abtest=True,
            points=settings.POINTS_PER_AB_TEST_VOTE,
        )

        # Update challenge participation stats
        if challenge_id:
            from services.challenge_service import ChallengeService
            challenge_service = ChallengeService(self.db)
            await challenge_service.update_participation_stats(
                event_id=challenge_id,
                user_id=vote.user_id,
                stats_data=eval_stats
            )

        from services.language_service import LanguageService
        language_service = LanguageService(self.db)
        await language_service.user_language_repository.update_language_stats(
            user_id=vote.user_id,
            language_id=language_id,
            stats_data=eval_stats
        )

        # Check if all pairs in this stage are complete
        stmt = select(ABTestPair).where(
            and_(
                ABTestPair.ab_test_id == ab_test.id,
                ABTestPair.stage_number == pair.stage_number
            )
        )

        pairs_result = await self.db.execute(stmt)
        all_pairs = pairs_result.scalars().all()
        all_pairs_complete = all(p.is_complete for p in all_pairs)

        # Determine if we should complete the AB test or advance to next stage
        can_advance = all_pairs_complete

        # Save changes
        await self.db.commit()

        return {
            "success": True,
            "can_advance": can_advance,
        }

    async def _mark_contribution_as_winner(self, contribution_id: uuid.UUID, contribution_type: str) -> None:
        """Mark a contribution as the winner (passed and accepted)"""
        contribution_model, _ = await self._get_models(contribution_type)

        stmt = (
            update(contribution_model)
            .where(contribution_model.id == contribution_id)
            .values(passed=True, accepted=True)
        )

        await self.db.execute(stmt)

    async def finalize_ab_test(self, ab_test_id: uuid.UUID) -> Dict[str, Any]:
        """
        Finalize an A/B test, determining the overall winner

        Returns:
            Dict with results information
        """
        ab_test = await self.get_ab_test(ab_test_id)

        if ab_test.is_complete:
            return {
                "ab_test_id": ab_test.id,
                "is_complete": True,
                "final_winner": ab_test.ab_test_data.get("final_winner")
            }

        # Check current state
        active_stage = None
        for stage in ab_test.ab_test_data["stages"]:
            if not stage["complete"]:
                active_stage = stage
                break

        if active_stage:
            # Need to calculate a winner for this stage
            winners = []
            for pair_results in active_stage["results"].values():
                # Count votes for each contribution
                vote_counts = {}
                for vote in pair_results.values():
                    vote_counts[vote] = vote_counts.get(vote, 0) + 1

                # Find the winner for this pair
                if vote_counts:
                    winner = max(vote_counts.items(), key=lambda x: x[1])[0]
                    winners.append(winner)

            # For pairs without votes, take the first element
            for pair in active_stage["pairs"]:
                pair_id = f"{pair[0]}_{pair[1]}"
                if pair_id not in active_stage["results"] or not active_stage["results"][pair_id]:
                    winners.append(pair[0])

            # Store stage winners and mark as complete
            active_stage["complete"] = True
            ab_test.ab_test_data["stage_winners"].append(winners)

        # Get all stage winners
        all_winners = []
        for winners in ab_test.ab_test_data["stage_winners"]:
            all_winners.extend(winners)

        # If no winners yet, take the last contribution from each pair in the first stage
        if not all_winners and ab_test.ab_test_data["stages"]:
            first_stage = ab_test.ab_test_data["stages"][0]
            all_winners = [pair[0] for pair in first_stage["pairs"]]

        # Count votes across all stages
        winner_counts = {}
        for winner in all_winners:
            winner_counts[winner] = winner_counts.get(winner, 0) + 1

        # Find the overall winner
        if winner_counts:
            final_winner = max(winner_counts.items(), key=lambda x: x[1])[0]
            ab_test.ab_test_data["final_winner"] = final_winner
            ab_test.is_complete = True

            # Mark the winning contribution as passed/accepted
            await self._mark_contribution_as_winner(
                uuid.UUID(final_winner),
                ab_test.ab_test_data["contribution_type"]
            )

        else:
            # No winner could be determined
            ab_test.is_complete = True

        await self.db.commit()

        return {
            "ab_test_id": ab_test.id,
            "is_complete": True,
            "final_winner": ab_test.ab_test_data.get("final_winner")
        }
