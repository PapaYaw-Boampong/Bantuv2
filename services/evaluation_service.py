import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from models import EvaluationInstance, EvaluationBranch
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_instance(self, sample_id: uuid.UUID, sample_type: str) -> EvaluationInstance:
        """
        Creates a new evaluation instance associated with a specific sample.
        :param sample_id: The ID of the sample (e.g., TranscriptionSample, TranslationSample, AnnotationSample)
        :param sample_type: The type of the sample (transcription, translation, annotation)
        :return: Created evaluation instance
        """
        try:
            evaluation_instance = EvaluationInstance(
                id=uuid.uuid4(),
                sample_id=sample_id,
                num_branches=3,  # Example: number of evaluation branches
                max_depth=5,  # Example: max depth of evaluation
                is_complete=False
            )

            # Associate the evaluation instance with a sample (based on sample_type)
            if sample_type == "transcription":
                evaluation_instance.transcription_sample_id = sample_id
            elif sample_type == "translation":
                evaluation_instance.translation_sample_id = sample_id
            elif sample_type == "annotation":
                evaluation_instance.annotation_sample_id = sample_id
            else:
                raise HTTPException(status_code=400, detail="Invalid sample type provided")

            self.db.add(evaluation_instance)
            await self.db.commit()
            await self.db.refresh(evaluation_instance)
            return evaluation_instance

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating evaluation instance: {str(e)}"
            )

    async def create_branch(self, instance_id: uuid.UUID) -> EvaluationBranch:
        """
        Creates a new evaluation branch for the provided evaluation instance.
        :param instance_id: The ID of the evaluation instance
        :return: Created evaluation branch
        """
        try:
            branch = EvaluationBranch(
                instance_id=instance_id,
                current_contribution_id=None,  # To be filled when contributions are evaluated
                depth=0,  # Starting depth
                complete=False  # Will be set to True when the branch evaluation is done
            )

            self.db.add(branch)
            await self.db.commit()
            await self.db.refresh(branch)
            return branch

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating evaluation branch: {str(e)}"
            )

    async def update_progress(self, branch_id: uuid.UUID, is_complete: bool) -> EvaluationBranch:
        """
        Updates the progress of an evaluation branch.
        :param branch_id: The ID of the evaluation branch
        :param is_complete: Whether the evaluation branch is complete
        :return: Updated evaluation branch
        """
        try:
            branch = await self.db.get(EvaluationBranch, branch_id)
            if not branch:
                raise HTTPException(status_code=404, detail="Branch not found")

            branch.complete = is_complete
            await self.db.commit()

            # Check if all branches are complete and update the evaluation instance
            evaluation_instance = await self.db.get(EvaluationInstance, branch.instance_id)
            if all(b.complete for b in evaluation_instance.branches):
                evaluation_instance.is_complete = True
                await self.db.commit()

            return branch

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error updating branch progress: {str(e)}"
            )

    async def delete_instance(self, instance_id: uuid.UUID) -> bool:
        """
        Deletes an evaluation instance and associated data.
        :param instance_id: The ID of the evaluation instance to be deleted
        :return: True if deletion is successful, False otherwise
        """
        try:
            evaluation_instance = await self.db.get(EvaluationInstance, instance_id)

            if not evaluation_instance:
                raise HTTPException(status_code=404, detail="Evaluation instance not found")

            # Delete associated branches
            for branch in evaluation_instance.branches:
                await self.db.delete(branch)

            # Delete the evaluation instance
            await self.db.delete(evaluation_instance)

            # Optionally, delete the sample associated with the evaluation instance
            if evaluation_instance.transcription_sample:
                await self.db.delete(evaluation_instance.transcription_sample)
            if evaluation_instance.translation_sample:
                await self.db.delete(evaluation_instance.translation_sample)
            if evaluation_instance.annotation_sample:
                await self.db.delete(evaluation_instance.annotation_sample)

            await self.db.commit()
            return True

        except SQLAlchemyError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting evaluation instance: {str(e)}"
            )

