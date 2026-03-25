import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job_repository import JobRepository
from app.scrapers import SCRAPERS
from app.scrapers.base import JobRaw

logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self, session: AsyncSession) -> None:
        self.job_repo = JobRepository(session)

    async def run(
        self,
        query: str,
        location: str = "",
        sources: list[str] | None = None,
        max_pages: int = 3,
    ) -> dict:
        """Run scrapers for requested sources and persist results."""
        sources = sources or list(SCRAPERS.keys())
        all_jobs: list[JobRaw] = []

        for source in sources:
            scraper_cls = SCRAPERS.get(source)
            if not scraper_cls:
                logger.warning("Unknown source: %s — skipping", source)
                continue
            logger.info("Starting scraper: %s", source)
            try:
                scraper = scraper_cls()
                jobs = await scraper.fetch(query, location, max_pages)
                all_jobs.extend(jobs)
                logger.info("%s: fetched %d jobs", source, len(jobs))
            except Exception as e:
                logger.error("%s scraper failed: %s", source, e)

        total_fetched = len(all_jobs)
        if not all_jobs:
            return {"fetched": 0, "upserted": 0}

        # Filter by location if provided — job boards sometimes leak off-location results
        if location:
            location_lower = location.lower()
            all_jobs = [
                job for job in all_jobs
                if job.location is None or location_lower in job.location.lower()
            ]
            logger.info(
                "Location filter '%s': %d → %d jobs", location, total_fetched, len(all_jobs)
            )

        if not all_jobs:
            return {"fetched": total_fetched, "upserted": 0}

        # Deduplicate by source_url within this batch before inserting
        seen_urls: set[str] = set()
        unique_jobs: list[JobRaw] = []
        for job in all_jobs:
            if job.source_url not in seen_urls:
                seen_urls.add(job.source_url)
                unique_jobs.append(job)
        logger.info("Deduped batch: %d → %d unique jobs", len(all_jobs), len(unique_jobs))

        now = datetime.now(timezone.utc)
        jobs_data = [
            {
                "id": uuid.uuid4(),
                "title": job.title,
                "source": job.source,
                "source_url": job.source_url,
                "company": job.company,
                "location": job.location,
                "description": job.description,
                "salary_range": job.salary_range,
                "job_type": job.job_type,
                "posted_at": job.posted_at,
                "scraped_at": now,
                "raw_html": job.raw_html,
                "is_active": True,
                "applied": False,
                "created_at": now,
                "updated_at": now,
            }
            for job in unique_jobs
        ]

        upserted = await self.job_repo.upsert_many(jobs_data)
        logger.info("Upserted %d jobs into DB (total fetched: %d)", upserted, total_fetched)
        return {"fetched": total_fetched, "location_filtered": len(all_jobs), "unique": len(unique_jobs), "upserted": upserted}
