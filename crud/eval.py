# from typing import List, Optional, Dict, Any
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
#
#
# class EvalCrud:
#     def __init__(self, db: AsyncSession):
#         self.db = db
#
#     async def create(self, evaluation_data: Dict[str, Any]) -> Evaluation:
#         """
#         Create a new evaluation (ASYNC)
#         """
#         evaluation = Evaluation(**evaluation_data)
#         self.db.add(evaluation)
#         await self.db.commit()
#         await self.db.refresh(evaluation)
#         return evaluation
#
#     async def get_by_id(self, evaluation_id: str) -> Optional[Evaluation]:
#         """
#         Get an evaluation by ID (ASYNC)
#         """
#         statement = select(Evaluation).where(Evaluation.id == evaluation_id)
#         result = await self.db.execute(statement)
#         return result.scalars().first()
#
#     async def get_by_user_id(self, user_id: str) -> List[Evaluation]:
#         """
#         Get all evaluations for a user (ASYNC)
#         """
#         statement = select(Evaluation).where(Evaluation.evaluator_user_id == user_id)
#         result = await self.db.execute(statement)
#         return result.scalars().all()
#
#     async def get_by_contribution_id(self, contribution_id: str) -> List[Evaluation]:
#         """
#         Get all evaluations for a specific contribution (ASYNC)
#         """
#         statement = select(Evaluation).where(Evaluation.contribution_user_id == contribution_id)
#         result = await self.db.execute(statement)
#         return result.scalars().all()
#
#     async def update(self, evaluation_id: str, evaluation_data: Dict[str, Any]) -> Optional[Evaluation]:
#         """
#         Update an evaluation (ASYNC)
#         """
#         statement = select(Evaluation).where(Evaluation.id == evaluation_id)
#         result = await self.db.execute(statement)
#         evaluation = result.scalars().first()
#
#         if evaluation:
#             for key, value in evaluation_data.items():
#                 setattr(evaluation, key, value)
#             await self.db.commit()
#             await self.db.refresh(evaluation)
#             return evaluation
#         return None
