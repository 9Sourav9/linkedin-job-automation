import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tailored_resume import TailoredResume
from app.repositories.base import BaseRepository


class TailoredResumeRepository(BaseRepository[TailoredResume]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TailoredResume, session)

    async def list_by_job(
        self, job_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> tuple[int, list[TailoredResume]]:
        from sqlalchemy import func

        count_result = await self.session.execute(
            select(func.count())
            .select_from(TailoredResume)
            .where(TailoredResume.job_id == job_id)
        )
        total = count_result.scalar_one()
        result = await self.session.execute(
            select(TailoredResume)
            .where(TailoredResume.job_id == job_id)
            .order_by(TailoredResume.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return total, list(result.scalars().all())
