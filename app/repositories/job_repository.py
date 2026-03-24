import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.repositories.base import BaseRepository
from app.schemas.job import JobCreate


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Job, session)

    async def get_by_source_url(self, source_url: str) -> Job | None:
        result = await self.session.execute(
            select(Job).where(Job.source_url == source_url)
        )
        return result.scalar_one_or_none()

    async def upsert_many(self, jobs_data: list[dict]) -> int:
        """Atomically insert or update jobs. Returns count of newly inserted rows."""
        if not jobs_data:
            return 0

        stmt = insert(Job).values(jobs_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_url"],
            set_={
                "raw_html": stmt.excluded.raw_html,
                "updated_at": datetime.now(timezone.utc),
                "is_active": True,
            },
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def list_by_source(
        self, source: str, offset: int = 0, limit: int = 50
    ) -> tuple[int, list[Job]]:
        from sqlalchemy import func

        count_result = await self.session.execute(
            select(func.count()).select_from(Job).where(Job.source == source)
        )
        total = count_result.scalar_one()
        result = await self.session.execute(
            select(Job)
            .where(Job.source == source)
            .order_by(Job.scraped_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return total, list(result.scalars().all())
