import uuid
from typing import Dict, List, Optional, Union, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

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
    User
)

from schemas.contribution import (
    ContributionFilter,
)

# Helper Methods
from utils.eval_service_utils import (
    filter_user_participated,
    prioritize_branches,
    is_expired,
    create_pairs,
    create_stage,
    get_active_stage,
    tally_pair_votes
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
            num_branches: int = 3,
            max_depth: int = 5,
    ) -> EvaluationInstance:
        """
        Initialize an evaluation instance for a given sample.

        Args:
            sample_id: The ID of the sample to evaluate
            contribution_type: "annotation", "transcription", or "translation"
            num_branches: Number of parallel evaluation branches
            max_depth: Maximum depth for each branch

        Returns:
            The created EvaluationInstance
        """
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
        await self.db.commit()
        await self.db.refresh(instance)

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

        # 2. Get contributions from ContributionManagementService
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
                contribution_id=contribution_ids[i],
                is_complete=False,
                head=True,
                step_number=1,
            )
            self.db.add(step)

        await self.db.commit()

        # Refresh instance to get created branches
        stmt = select(EvaluationInstance).where(EvaluationInstance.id == instance.id)
        result = await self.db.execute(stmt)
        instance = result.scalars().first()

        return instance

    # =========== Managing Evaluation Steps ==========
    async def submit_evaluation_step(
            self,
            branch_id: uuid.UUID,
            instance_id: uuid.UUID,
            language_id: uuid.UUID,
            user_id: uuid.UUID,
            contribution_type: str,
            rating: Optional[int] = None,
            decision: Optional[bool] = None,
            correction_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Submit and progress an evaluation step in a branch.

        Args:
            branch_id: ID of the evaluation branch
            instance_id: ID of the evaluation instance
            contribution_type: Type of contribution ("annotation", "transcription", "translation")
            rating: Optional rating given by evaluator
            decision: Whether the current contribution was upvoted
            correction_id: New contribution to use if current was rejected
            language_id: ID of the language for the evaluation
            user_id: ID of the user submitting the evaluation

        Returns:
            True if submission was successful

        """
        if decision is None:
            # Treat as a skipped evaluation — no stat increment or contribution change
            pass

        # 1. Get the branch and check for completion
        branch = await self.get_branch(branch_id)

        # 2. Handle contribution resolution
        from services.contribution_service import ContributionManagementService
        contribution_management_service = ContributionManagementService(self.db)

        if decision is False:
            # Use correction (assumes it’s already created & valid)
            if not correction_id:
                raise ValueError(
                    "Correction ID must be provided if contribution is not upvoted")  # will possibly remove for skipped
            branch.current_contribution_id = correction_id
        elif decision is True:
            await contribution_management_service.upvote_contribution(
                contribution_id=branch.current_contribution_id,
                contribution_type=contribution_type,
            )

        # 3. Mark current head step as complete and not head
        await self.db.execute(
            update(EvaluationStep)
            .where(
                and_(
                    EvaluationStep.branch_id == branch_id,
                    EvaluationStep.head == True
                )
            )
            .values(head=False, is_complete=True)
        )
        # Prepare next step or finish instance
        if branch.is_complete:
            # 4. Check if instance is complete
            await self._check_instance_completion(instance_id)
        else:
            # 5. Increment branch depth and create next evaluation step
            branch.depth += 1
            next_step = EvaluationStep(
                branch_id=branch.id,
                instance_id=instance_id,
                contribution_id=branch.current_contribution_id,
                head=True,
                complete=False,
                step_number=branch.depth + 1
            )
            self.db.add(next_step)

        # Update evaluator stats
        from services.language_service import LanguageService
        language_service = LanguageService(self.db)
        from services.challenge_service import ChallengeService

        eval_stats = {
            "is_evaluation": True,
            "evaluation_count": 1,
            "points": settings.EVALUATION_POINTS,
        }
        # Update challenge participation stats
        if branch.event_id:
            challenge_service = ChallengeService(self.db)
            await challenge_service.update_participation_stats(
                event_id=branch.event_id,
                user_id=user_id,
                stats_data=eval_stats
            )
        await language_service.user_language_repository.update_language_stats(
            user_id=user_id,
            language_id=language_id,
            stats_data=eval_stats
        )

        # Commit everything
        await self.db.commit()
        return True

    async def get_evaluation_step(self, step_id: uuid.UUID) -> EvaluationStep:
        """Get an evaluation step by ID"""
        condition = EvaluationStep.id == step_id
        stmt = select(EvaluationStep).where(condition)  # type: ignore
        result = await self.db.execute(stmt)
        step: EvaluationStep | None = result.scalars().first()

        # Check if step exists
        if not step:
            raise ValueError(f"Step with ID {step_id} not found")

        return step

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
    async def finalize_evaluation_instance(
            self, instance_id: uuid.UUID,
            contribution_type: str
    ) -> bool:
        """
        Forcefully finalize an evaluation instance.

        Returns:
            True if successful, False otherwise
        """
        instance = await self.get_evaluation_instance(instance_id)

        if instance.is_complete:
            return True

        # Mark all branches as complete
        for branch in instance.branches:
            branch.complete = True

        instance.is_complete = True
        await self.db.commit()

        # If A/B test is required, initialize it
        if instance.ab_test:
            await self.init_ab_test(
                instance.id,
                contribution_type=contribution_type
            )

        return True

    async def assign_evaluation_step_to_user(
            self,
            user_id: uuid.UUID,
            proficiency_level: int,
            contribution_type: str,
            challenge_id: Optional[uuid.UUID] = None,
            language_id: Optional[uuid.UUID] = None,
            num_steps: int = 1,
    ) -> List[dict]:
        assignments = []

        branches = await self._get_candidate_branches_with_head_steps(challenge_id)
        branches = filter_user_participated(branches, user_id)
        prioritized = prioritize_branches(branches, proficiency_level)

        steps_assigned = 0

        # 1. Assign from existing prioritized branches
        for branch in prioritized:
            if steps_assigned >= num_steps:
                break

            step = await self._assign_or_create_step(user_id, branch)

            assignments.append({
                "task_type": "evaluation_step",
                "branch_id": str(branch.id),
                "depth": len(branch.evaluation_steps),
                "max_depth": branch.max_depth,
                "step_id": str(step.id),
                "head": step.head,
                "note": "Assigned from existing branch"
            })
            steps_assigned += 1

        # 2. If not enough, create new evaluation instances
        if steps_assigned < num_steps:
            remaining = num_steps - steps_assigned

            _, model = self.task_type[contribution_type]
            from services.sample_data_service import SampleDataService
            sample_data_service = SampleDataService(self.db)
            sample_ids = await sample_data_service.get_samples(
                model, contribution_type,
                language_id=language_id,
                limit=remaining,
                ids_only=True
            )

            for sample_id in sample_ids:
                instance = await self.create_evaluation_instance(
                    sample_id=sample_id,
                    contribution_type=contribution_type,
                    num_branches=3,
                    max_depth=5
                )
                branch = instance.evaluation_branches[0]
                step = branch.evaluation_steps[0]
                step.user_id = user_id
                step.assigned_at = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(step)

                assignments.append({
                    "task_type": "evaluation_step",
                    "branch_id": str(branch.id),
                    "depth": 1,
                    "max_depth": branch.max_depth,
                    "step_id": str(step.id),
                    "head": step.head,
                    "note": "New evaluation instance created due to shortage"
                })

                steps_assigned += 1
                if steps_assigned >= num_steps:
                    break

        return assignments

    async def _get_candidate_branches_with_head_steps(
            self,
            challenge_id: Optional[uuid.UUID]
    ) -> List[EvaluationBranch]:
        stmt = (
            select(EvaluationBranch)
            .join(EvaluationInstance)
            .join(EvaluationStep)
            .options(
                selectinload(EvaluationBranch.evaluation_steps),
                selectinload(EvaluationBranch.evaluation_instance),
            )
            .where(EvaluationBranch.is_complete == False)
            # .where(EvaluationInstance.is_complete == False)
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

        if challenge_id:
            stmt = stmt.where(EvaluationInstance.challenge_id == challenge_id)
        else:
            stmt = stmt.where(EvaluationInstance.challenge_id.is_(None))

        result = await self.db.execute(stmt)
        branches: List[EvaluationBranch] = result.scalars().unique().all()
        return branches

    async def _assign_or_create_step(
            self,
            user_id: uuid.UUID,
            branch: EvaluationBranch
    ) -> EvaluationStep:
        head_step = next((s for s in branch.evaluation_steps if s.head), None)

        # Reassign if unassigned or expired
        if head_step and (head_step.user_id is None or is_expired(head_step)):
            head_step.user_id = user_id
            head_step.assigned_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(head_step)
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
        self.db.add(new_step)
        await self.db.commit()
        await self.db.refresh(new_step)
        return new_step

    async def select_top_contributions(
            self,
            instance_id: uuid.UUID,
            contribution_type: str,
            limit: int = 5
    ) -> List[Union[AnnotationContribution, TranscriptionContribution, TranslationContribution]]:
        """
        Select top contributions for a sample by combining upvotes with word frequency scores.
        """

        from services.contribution_service import ContributionManagementService

        contribution_management_service = ContributionManagementService(self.db)

        # 1. Get sample & evaluation instance
        _, sample_model = await self._get_models(contribution_type)
        stmt = select(sample_model).where(sample_model.evaluation_instance_id == instance_id)
        sample = (await self.db.execute(stmt)).scalars().first()

        if not sample:
            raise ValueError(f"No sample found for eval instance {instance_id} for {contribution_type}")

        instance = sample.evaluation_instance
        if not instance or not instance.is_complete:
            raise ValueError(f"Evaluation instance Incomplete")

        # 2. Get contributions from ContributionManagementService
        filters = ContributionFilter(
            evaluation_instance_id=instance_id,
            active=True,
            flagged=False
        )

        contributions = await contribution_management_service.list_contributions(
            contribution_type=contribution_type,
            filters=filters,
            skip=0,
            limit=100
        )

        if not contributions:
            return []

        # 3. Get word frequencies for sample
        word_freq: dict[str, int] = sample.words

        # 4. Score contributions
        def compute_score(contribution) -> float:
            text = getattr(contribution, "text", "")
            words = text.lower().split()
            word_score = sum(word_freq.get(word, 0) for word in words)
            # return 0.7 * upvotes + 0.3 * word_score
            return contribution.upvotes + word_score

        scored_contributions = [(c, compute_score(c)) for c in contributions]
        scored_contributions.sort(key=lambda x: x[1], reverse=True)

        top_contributions = [c for c, _ in scored_contributions[:limit]]
        return top_contributions

    # =========== A/B Testing ==========

    async def init_ab_test(self, instance_id: uuid.UUID, contribution_type: str) -> ABTest:
        """
        Initialize A/B testing for an evaluation instance.
        Creates pairwise comparisons of the top contributions.

        Returns:
            The created ABTest instance
        """
        instance = await self.get_evaluation_instance(instance_id)

        if not instance.is_complete:
            raise ValueError(f"Cannot initialize A/B test - instance {instance_id} is not complete")

        if not contribution_type:
            raise ValueError(f"Could not determine contribution type for instance {instance_id}")

        if contribution_type not in self.task_type:
            raise ValueError(f"Invalid contribution type: {contribution_type}")

        # Get top contributions
        top_contributions = await self.select_top_contributions(
            instance_id=instance_id,
            contribution_type=contribution_type,
            limit=6  # Get top 6 for A/B comparisons
        )

        if len(top_contributions) < 2:
            raise ValueError(f"Not enough contributions for A/B testing. Need at least 2, got {len(top_contributions)}")

        # Prepare initial A/B test stage using helper
        stage = create_stage(
            create_pairs([str(c.id) for c in top_contributions])
        )

        ab_test_data = {
            "contribution_type": contribution_type,
            "stages": [stage],
            "final_winner": None,
            "stage_winners": []
        }

        ab_test = ABTest(
            instance_id=instance.id,
            is_complete=False,
            ab_test=True,
            ab_test_data=ab_test_data
        )

        self.db.add(ab_test)
        await self.db.commit()
        await self.db.refresh(ab_test)

        return ab_test

    async def advance_ab_test(self, ab_test_id: uuid.UUID):

        ab_test = await self.get_ab_test(ab_test_id)
        if not ab_test:
            raise ValueError(f"No ABTest found with ID {ab_test_id}")

        last_stage = ab_test.ab_test_data["stages"][-1]
        if not last_stage["complete"]:
            raise ValueError("Last stage is not complete")

        # Gather winners
        winners = [result["winner"] for result in last_stage["results"].values()]

        if len(winners) == 1:
            ab_test.ab_test_data["final_winner"] = winners[0]
            ab_test.is_complete = True
            await self.db.commit()
            return ab_test

        next_stage = create_stage(create_pairs(winners))

        ab_test.ab_test_data["stages"].append(next_stage)
        ab_test.ab_test_data["stage_winners"] = winners

        await self.db.commit()
        await self.db.refresh(ab_test)
        return ab_test

    async def get_ab_test(self, ab_test_id: uuid.UUID) -> ABTest:
        """Get an A/B test by ID"""
        stmt = select(ABTest).where(ABTest.id == ab_test_id)
        result = await self.db.execute(stmt)
        ab_test = result.scalars().first()

        if not ab_test:
            raise ValueError(f"A/B test with ID {ab_test_id} not found")

        return ab_test

    async def get_ab_test_for_instance(self, instance_id: uuid.UUID) -> Optional[ABTest]:
        """Get the A/B test for an evaluation instance"""
        stmt = select(ABTest).where(ABTest.instance_id == instance_id)
        result = await self.db.execute(stmt)
        ab_test = result.scalars().first()

        return ab_test

    async def assign_ab_test_to_user(
            self,
            ab_test_id: uuid.UUID,
            user_id: uuid.UUID,
            proficiency_level: int = 1
    ) -> Dict[str, Any]:
        """
        Assign an A/B test comparison to a user

        Args:
            ab_test_id: ID of A/B test
            user_id: ID of user to assign to
            proficiency_level: User's proficiency level (1-5)

        Returns:
            Dict with the pair of contributions to compare
        """
        ab_test = await self.get_ab_test(ab_test_id)

        if ab_test.is_complete:
            raise ValueError(f"A/B test {ab_test_id} is already complete")

        # Only assign to high proficiency users for A/B tests
        if proficiency_level < 3:
            raise ValueError(f"User proficiency level {proficiency_level} is too low for A/B testing (minimum 3)")

        # Find current active stage
        active_stage = get_active_stage(ab_test.ab_test_data)

        if not active_stage:
            raise ValueError(f"No active stages found in A/B test {ab_test_id}")

        # Find a pair that hasn't been assigned to this user
        user_id_str = str(user_id)
        assigned_pair = None

        for pair in active_stage["pairs"]:
            pair_id = f"{pair[0]}_{pair[1]}"
            if pair_id not in active_stage["results"] or user_id_str not in active_stage["results"][pair_id]:
                assigned_pair = pair
                break

        if not assigned_pair:
            raise ValueError(f"No available pairs to assign to user {user_id}")

        # Get contribution details
        contribution_type = ab_test.ab_test_data["contribution_type"]
        contribution_model, _ = await self._get_models(contribution_type)

        stmt = (
            select(contribution_model)
            .where(contribution_model.id.in_([uuid.UUID(assigned_pair[0]), uuid.UUID(assigned_pair[1])]))
        )

        result = await self.db.execute(stmt)
        contributions = {str(c.id): c for c in result.scalars().all()}

        # Return the pair information
        return {
            "ab_test_id": ab_test.id,
            "stage_id": active_stage["stage_id"],
            "pair": assigned_pair,
            "contributions": [
                {
                    "id": assigned_pair[0],
                    "content": contributions[assigned_pair[0]].target_text if hasattr(contributions[assigned_pair[0]],
                                                                                      "target_text") else contributions[
                        assigned_pair[0]].target_url,
                    "upvotes": contributions[assigned_pair[0]].upvotes
                },
                {
                    "id": assigned_pair[1],
                    "content": contributions[assigned_pair[1]].target_text if hasattr(contributions[assigned_pair[1]],
                                                                                      "target_text") else contributions[
                        assigned_pair[1]].target_url,
                    "upvotes": contributions[assigned_pair[1]].upvotes
                }
            ]
        }

    async def submit_ab_test_result(
            self,
            ab_test_id: uuid.UUID,
            stage_id: str,
            user_id: uuid.UUID,
            selected_contribution_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Submit a user's selection for an A/B test comparison

        Args:
            ab_test_id: ID of the A/B test
            stage_id: ID of the stage
            user_id: ID of the user submitting the result
            selected_contribution_id: ID of the selected contribution

        Returns:
            Dict with updated stage information
        """
        ab_test = await self.get_ab_test(ab_test_id)

        if ab_test.is_complete:
            raise ValueError(f"A/B test {ab_test_id} is already complete")

        # Find the stage
        stage = None
        stage_index = -1
        for i, s in enumerate(ab_test.ab_test_data["stages"]):
            if s["stage_id"] == stage_id:
                stage = s
                stage_index = i
                break

        if not stage:
            raise ValueError(f"Stage {stage_id} not found in A/B test {ab_test_id}")

        if stage["complete"]:
            raise ValueError(f"Stage {stage_id} is already complete")

        # Find the pair that contains the selected contribution
        selected_id_str = str(selected_contribution_id)
        pair_id = None

        for pair in stage["pairs"]:
            if selected_id_str in pair:
                pair_id = f"{pair[0]}_{pair[1]}"
                break

        if not pair_id:
            raise ValueError(f"Selected contribution {selected_contribution_id} not found in any pair")

        # Initialize results for this pair if needed
        if pair_id not in stage["results"]:
            stage["results"][pair_id] = {}

        # Record the user's selection
        stage["results"][pair_id][str(user_id)] = selected_id_str

        # Get total number of votes for this stage
        total_votes = sum(len(results) for results in stage["results"].values())
        required_votes = len(stage["pairs"]) * 3  # Example: 3 votes per pair

        # Check if stage is complete
        if total_votes >= required_votes:
            stage["complete"] = True

            # Calculate stage winner(s)
            winners = [
                tally_pair_votes(pair_results)
                for pair_results in stage["results"].values()
                if tally_pair_votes(pair_results)
            ]

            # Store stage winners
            ab_test.ab_test_data["stage_winners"].append(winners)

            # Create next stage if needed
            if len(winners) > 1:
                next_stage = create_stage(create_pairs(winners))
                ab_test.ab_test_data["stages"].append(next_stage)
            else:
                # Final winner
                ab_test.ab_test_data["final_winner"] = winners[0]
                ab_test.is_complete = True

                # Mark the winning contribution as passed/accepted
                await self._mark_contribution_as_winner(
                    uuid.UUID(winners[0]),
                    ab_test.ab_test_data["contribution_type"]
                )

        # Save changes
        await self.db.commit()

        return {
            "stage_complete": stage["complete"],
            "ab_test_complete": ab_test.is_complete,
            "final_winner": ab_test.ab_test_data.get("final_winner"),
            "next_stage_id":
                ab_test.ab_test_data["stages"][stage_index + 1]["stage_id"] if stage[
                                                                                   "complete"] and not ab_test.is_complete else None
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

    # =========== User Assignment ==========
