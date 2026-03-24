import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.core.config import settings
from app.scrapers.base import BaseScraper, JobRaw

logger = logging.getLogger(__name__)

INDEED_BASE = "https://www.indeed.com/jobs"


class IndeedScraper(BaseScraper):
    source = "indeed"

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
                start = page_num * 10
                url = (
                    f"{INDEED_BASE}?q={quote_plus(query)}"
                    f"&l={quote_plus(location)}&start={start}"
                )
                logger.info("Indeed: fetching page %d — %s", page_num + 1, url)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await self._random_delay()
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await self._random_delay()

                    html = await page.content()
                    page_jobs = self._parse_jobs(html)
                    if not page_jobs:
                        logger.info("Indeed: no more results at page %d", page_num + 1)
                        break
                    jobs.extend(page_jobs)
                    logger.info("Indeed: collected %d jobs so far", len(jobs))
                except Exception as e:
                    logger.error("Indeed: error on page %d: %s", page_num + 1, e)
                    break

            await browser.close()

        return jobs

    def _parse_jobs(self, html: str) -> list[JobRaw]:
        soup = BeautifulSoup(html, "lxml")
        job_cards = soup.select("div.job_seen_beacon, td.resultContent")

        results: list[JobRaw] = []
        for card in job_cards:
            try:
                title_el = card.select_one("h2.jobTitle a, a.jcs-JobTitle")
                company_el = card.select_one("span.companyName, [data-testid='company-name']")
                location_el = card.select_one("div.companyLocation, [data-testid='text-location']")
                salary_el = card.select_one("div.salary-snippet-container, [data-testid='attribute_snippet_testid']")

                if not title_el:
                    continue

                href = title_el.get("href", "")
                if href.startswith("/"):
                    source_url = "https://www.indeed.com" + href.split("?")[0]
                else:
                    source_url = href.split("?")[0]

                if not source_url:
                    continue

                results.append(
                    JobRaw(
                        title=title_el.get_text(strip=True),
                        source=self.source,
                        source_url=source_url,
                        company=company_el.get_text(strip=True) if company_el else None,
                        location=location_el.get_text(strip=True) if location_el else None,
                        salary_range=salary_el.get_text(strip=True) if salary_el else None,
                        raw_html=str(card),
                    )
                )
            except Exception as e:
                logger.warning("Indeed: failed to parse card: %s", e)
                continue

        return results
