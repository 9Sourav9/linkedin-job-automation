import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.core.config import settings


@dataclass
class JobRaw:
    """Plain dataclass — scrapers are DB-agnostic."""
    title: str
    source: str
    source_url: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    salary_range: str | None = None
    job_type: str | None = None
    posted_at: datetime | None = None
    raw_html: str | None = None


class BaseScraper(ABC):
    source: str = ""

    async def _random_delay(self) -> None:
        delay = random.uniform(settings.scraper_delay_min, settings.scraper_delay_max)
        await asyncio.sleep(delay)

    @abstractmethod
    async def fetch(
        self, query: str, location: str = "", max_pages: int = 3
    ) -> list[JobRaw]:
        """Scrape jobs and return raw job data."""
        ...
