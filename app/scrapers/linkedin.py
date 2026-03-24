import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.core.config import settings
from app.scrapers.base import BaseScraper, JobRaw

logger = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com/jobs/search"


class LinkedInScraper(BaseScraper):
    source = "linkedin"

    async def fetch(
        self, query: str, location: str = "", max_pages: int = 3
    ) -> list[JobRaw]:
        jobs: list[JobRaw] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=settings.scraper_headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            for page_num in range(max_pages):
                start = page_num * 25
                url = (
                    f"{LINKEDIN_BASE}?keywords={quote_plus(query)}"
                    f"&location={quote_plus(location)}&start={start}"
                )
                logger.info("LinkedIn: fetching page %d — %s", page_num + 1, url)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await self._random_delay()

                    # Scroll to load lazy content
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await self._random_delay()

                    html = await page.content()
                    page_jobs = self._parse_jobs(html)
                    if not page_jobs:
                        logger.info("LinkedIn: no more results at page %d", page_num + 1)
                        break
                    jobs.extend(page_jobs)
                    logger.info("LinkedIn: collected %d jobs so far", len(jobs))
                except Exception as e:
                    logger.error("LinkedIn: error on page %d: %s", page_num + 1, e)
                    break

            await browser.close()

        return jobs

    def _parse_jobs(self, html: str) -> list[JobRaw]:
        soup = BeautifulSoup(html, "lxml")
        job_cards = soup.select("div.base-card")
        if not job_cards:
            job_cards = soup.select("li.jobs-search-results__list-item")

        results: list[JobRaw] = []
        for card in job_cards:
            try:
                title_el = card.select_one("h3.base-search-card__title, h3.job-card-list__title")
                company_el = card.select_one("h4.base-search-card__subtitle, a.job-card-container__company-name")
                location_el = card.select_one("span.job-search-card__location, li.job-card-container__metadata-item")
                link_el = card.select_one("a.base-card__full-link, a.job-card-list__title")
                time_el = card.select_one("time")

                if not title_el or not link_el:
                    continue

                title = title_el.get_text(strip=True)
                source_url = link_el.get("href", "").split("?")[0].strip()
                if not source_url:
                    continue

                posted_at: datetime | None = None
                if time_el and time_el.get("datetime"):
                    try:
                        posted_at = datetime.fromisoformat(time_el["datetime"]).replace(
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        pass

                results.append(
                    JobRaw(
                        title=title,
                        source=self.source,
                        source_url=source_url,
                        company=company_el.get_text(strip=True) if company_el else None,
                        location=location_el.get_text(strip=True) if location_el else None,
                        posted_at=posted_at,
                        raw_html=str(card),
                    )
                )
            except Exception as e:
                logger.warning("LinkedIn: failed to parse card: %s", e)
                continue

        return results
