"""
LinkedIn Job Scraper using Playwright.
Handles login, job search with filters, and job detail extraction.
"""
import json
import time
import random
from dataclasses import dataclass, field, asdict
from typing import Optional
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import config


@dataclass
class JobPosting:
    job_id: str
    title: str
    company: str
    location: str
    posted_date: str
    job_type: str
    remote_type: str
    job_url: str
    apply_url: str
    is_easy_apply: bool
    description: str = ""
    seniority_level: str = ""
    employment_type: str = ""
    industry: str = ""
    tailored_resume_path: str = ""
    application_status: str = "pending"
    error_msg: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class LinkedInScraper:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._logged_in = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = self.context.new_page()

    def close(self):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _human_delay(self, min_ms: int = 500, max_ms: int = 1500):
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    def _type_human(self, locator, text: str):
        """Type text with random delays to simulate human typing."""
        locator.click()
        self._human_delay(200, 400)
        for char in text:
            locator.type(char, delay=random.randint(50, 150))

    def login(self) -> bool:
        """Log into LinkedIn."""
        if self._logged_in:
            return True

        print("[LinkedIn] Navigating to login page...")
        self.page.goto(config.LINKEDIN_LOGIN_URL, wait_until="networkidle")
        self._human_delay(1000, 2000)

        # Fill email
        email_input = self.page.locator("#username")
        email_input.wait_for(state="visible", timeout=10000)
        self._type_human(email_input, config.LINKEDIN_EMAIL)

        # Fill password
        password_input = self.page.locator("#password")
        self._type_human(password_input, config.LINKEDIN_PASSWORD)

        # Click sign in
        self._human_delay(500, 1000)
        self.page.locator('button[type="submit"]').click()

        # Wait for navigation
        try:
            self.page.wait_for_url("**/feed/**", timeout=15000)
            self._logged_in = True
            print("[LinkedIn] Login successful.")
            return True
        except Exception:
            # Check for CAPTCHA or 2FA
            if "checkpoint" in self.page.url or "challenge" in self.page.url:
                print("[LinkedIn] 2FA / CAPTCHA detected. Please complete manually.")
                input("Press Enter after completing verification...")
                self._logged_in = True
                return True
            print("[LinkedIn] Login failed. Check credentials.")
            return False

    def _build_search_url(self, keyword: str) -> str:
        """Build LinkedIn job search URL with all filters."""
        params = [f"keywords={keyword.replace(' ', '%20')}"]

        if config.JOB_LOCATION:
            params.append(f"location={config.JOB_LOCATION.replace(' ', '%20').replace(',', '%2C')}")

        if config.JOB_DATE_FILTER:
            params.append(f"f_TPR={config.JOB_DATE_FILTER}")

        if config.JOB_TYPE:
            params.append(f"f_JT={config.JOB_TYPE}")

        if config.JOB_EXPERIENCE:
            levels = "%2C".join(config.JOB_EXPERIENCE.split(","))
            params.append(f"f_E={levels}")

        if config.JOB_REMOTE:
            params.append(f"f_WT={config.JOB_REMOTE}")

        return config.LINKEDIN_JOBS_URL + "?" + "&".join(params)

    def scrape_jobs(self, max_jobs: int = 25) -> list[JobPosting]:
        """Scrape jobs for all configured keywords."""
        if not self.login():
            raise RuntimeError("LinkedIn login failed.")

        all_jobs: list[JobPosting] = []
        seen_ids: set[str] = set()

        for keyword in config.JOB_KEYWORDS:
            print(f"\n[LinkedIn] Searching jobs: '{keyword}'")
            url = self._build_search_url(keyword)
            jobs = self._scrape_keyword_jobs(url, keyword, max_jobs, seen_ids)
            all_jobs.extend(jobs)
            seen_ids.update(j.job_id for j in jobs)
            print(f"[LinkedIn] Found {len(jobs)} jobs for '{keyword}'")

        print(f"\n[LinkedIn] Total unique jobs scraped: {len(all_jobs)}")
        return all_jobs

    def _scrape_keyword_jobs(
        self, url: str, keyword: str, max_jobs: int, seen_ids: set
    ) -> list[JobPosting]:
        self.page.goto(url, wait_until="networkidle")
        self._human_delay(2000, 3000)

        jobs: list[JobPosting] = []
        page_num = 0

        while len(jobs) < max_jobs:
            # Scroll to load all cards
            self._scroll_job_list()

            # Extract job cards from current page
            cards = self.page.locator(".job-card-container").all()
            print(f"  [Page {page_num + 1}] Found {len(cards)} cards")

            for card in cards:
                if len(jobs) >= max_jobs:
                    break
                try:
                    job = self._extract_job_card(card, seen_ids)
                    if job:
                        jobs.append(job)
                        seen_ids.add(job.job_id)
                except Exception as e:
                    print(f"  [Warning] Failed to extract card: {e}")

            # Try next page
            next_btn = self.page.locator('button[aria-label="View next page"]')
            if next_btn.count() > 0 and next_btn.is_enabled():
                next_btn.click()
                self._human_delay(2000, 3000)
                page_num += 1
            else:
                break

        return jobs

    def _scroll_job_list(self):
        """Scroll the job results panel to load all listings."""
        try:
            panel = self.page.locator(".jobs-search-results-list").first
            for _ in range(5):
                panel.evaluate("el => el.scrollBy(0, 600)")
                self._human_delay(300, 600)
            panel.evaluate("el => el.scrollTo(0, 0)")
        except Exception:
            pass

    def _extract_job_card(self, card, seen_ids: set) -> Optional[JobPosting]:
        """Extract basic info from a job card."""
        # Get job ID
        job_id = card.get_attribute("data-job-id") or ""
        if not job_id or job_id in seen_ids:
            return None

        # Click card to load details in sidebar
        card.click()
        self._human_delay(1500, 2500)

        try:
            # Wait for job details to load
            self.page.wait_for_selector(".jobs-unified-top-card__job-title", timeout=8000)
        except Exception:
            return None

        # Extract details from sidebar
        def safe_text(selector: str, default: str = "") -> str:
            el = self.page.locator(selector).first
            if el.count() > 0:
                return el.inner_text().strip()
            return default

        title = safe_text(".jobs-unified-top-card__job-title")
        company = safe_text(".jobs-unified-top-card__company-name")
        location = safe_text(".jobs-unified-top-card__bullet")
        posted_date = safe_text(".jobs-unified-top-card__posted-date")
        job_url = self.page.url

        # Check Easy Apply
        apply_btn = self.page.locator(".jobs-apply-button")
        is_easy_apply = False
        apply_url = job_url
        if apply_btn.count() > 0:
            btn_text = apply_btn.inner_text().strip().lower()
            is_easy_apply = "easy apply" in btn_text

        # Get job description
        description = ""
        try:
            desc_el = self.page.locator(".jobs-description__content").first
            if desc_el.count() > 0:
                description = desc_el.inner_text().strip()
        except Exception:
            pass

        # Get job metadata (type, seniority, etc.)
        job_type = ""
        seniority = ""
        employment_type = ""
        industry = ""
        try:
            criteria = self.page.locator(".description__job-criteria-item").all()
            for item in criteria:
                header = item.locator(".description__job-criteria-subheader").inner_text().strip().lower()
                value = item.locator(".description__job-criteria-text").inner_text().strip()
                if "seniority" in header:
                    seniority = value
                elif "employment type" in header:
                    employment_type = value
                    job_type = value
                elif "industries" in header:
                    industry = value
        except Exception:
            pass

        # Remote/hybrid detection
        remote_type = ""
        loc_lower = location.lower()
        if "remote" in loc_lower:
            remote_type = "Remote"
        elif "hybrid" in loc_lower:
            remote_type = "Hybrid"
        else:
            remote_type = "On-site"

        return JobPosting(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            posted_date=posted_date,
            job_type=job_type or employment_type,
            remote_type=remote_type,
            job_url=job_url,
            apply_url=apply_url,
            is_easy_apply=is_easy_apply,
            description=description,
            seniority_level=seniority,
            employment_type=employment_type,
            industry=industry,
        )

    def fetch_job_description(self, job_url: str) -> str:
        """Fetch full job description from a job URL."""
        self.page.goto(job_url, wait_until="networkidle")
        self._human_delay(1500, 2500)
        try:
            desc_el = self.page.locator(".jobs-description__content").first
            if desc_el.count() > 0:
                return desc_el.inner_text().strip()
        except Exception:
            pass
        return ""
