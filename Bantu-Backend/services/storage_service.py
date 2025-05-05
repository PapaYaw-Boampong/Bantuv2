from sqlmodel import select
from models.storage import MediaFile
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.storage import MediaFileRead


class StorageService:
    def __init__(self,  db: AsyncSession):
        self.db = db

    async def get_media_file_by_id(self, media_id):
        stmt = select(MediaFile).where(MediaFile.id == media_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
