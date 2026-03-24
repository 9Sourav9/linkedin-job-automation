import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.core.config import settings
from app.scrapers.base import BaseScraper, JobRaw

logger = logging.getLogger(__name__)

NAUKRI_BASE = "https://www.naukri.com"


class NaukriScraper(BaseScraper):
    source = "naukri"

    async def fetch(
        self, query: str, location: str = "", max_pages: int = 3
    ) -> list[JobRaw]:
        jobs: list[JobRaw] = []
        query_slug = "-".join(query.lower().split())
        location_slug = "-".join(location.lower().split()) if location else ""

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

            for page_num in range(1, max_pages + 1):
                if location_slug:
                    url = f"{NAUKRI_BASE}/{query_slug}-jobs-in-{location_slug}-{page_num}"
                else:
                    url = f"{NAUKRI_BASE}/{query_slug}-jobs-{page_num}"

                logger.info("Naukri: fetching page %d — %s", page_num, url)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await self._random_delay()
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await self._random_delay()

                    html = await page.content()
                    page_jobs = self._parse_jobs(html)
                    if not page_jobs:
                        logger.info("Naukri: no more results at page %d", page_num)
                        break
                    jobs.extend(page_jobs)
                    logger.info("Naukri: collected %d jobs so far", len(jobs))
                except Exception as e:
                    logger.error("Naukri: error on page %d: %s", page_num, e)
                    break

            await browser.close()

        return jobs

    def _parse_jobs(self, html: str) -> list[JobRaw]:
        soup = BeautifulSoup(html, "lxml")
        job_cards = soup.select("article.jobTuple, div.job-tuple-wrapper")

        results: list[JobRaw] = []
        for card in job_cards:
            try:
                title_el = card.select_one("a.title, a.jobTitle")
                company_el = card.select_one("a.subTitle, a.companyInfo")
                location_el = card.select_one("li.location, span.locWdth")
                salary_el = card.select_one("li.salary, span.salary")
                experience_el = card.select_one("li.experience, span.expwdth")

                if not title_el:
                    continue

                source_url = title_el.get("href", "").strip()
                if not source_url.startswith("http"):
                    source_url = NAUKRI_BASE + source_url

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
                logger.warning("Naukri: failed to parse card: %s", e)
                continue

        return results
