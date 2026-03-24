from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Resume, session)

    async def get_by_hash(self, content_hash: str) -> Resume | None:
        result = await self.session.execute(
            select(Resume).where(Resume.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def list_active(self, offset: int = 0, limit: int = 50) -> tuple[int, list[Resume]]:
        from sqlalchemy import func

        count_result = await self.session.execute(
            select(func.count()).select_from(Resume).where(Resume.is_active == True)
        )
        total = count_result.scalar_one()
        result = await self.session.execute(
            select(Resume)
            .where(Resume.is_active == True)
            .order_by(Resume.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return total, list(result.scalars().all())
