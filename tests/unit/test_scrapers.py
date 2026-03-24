from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.naukri import NaukriScraper
from app.scrapers.indeed import IndeedScraper


LINKEDIN_HTML = """
<div class="base-card">
  <h3 class="base-search-card__title">Senior Python Developer</h3>
  <h4 class="base-search-card__subtitle">Acme Corp</h4>
  <span class="job-search-card__location">Bangalore, India</span>
  <a class="base-card__full-link" href="https://linkedin.com/jobs/view/123456">View</a>
  <time datetime="2024-06-01T00:00:00Z">Posted 1 day ago</time>
</div>
"""

NAUKRI_HTML = """
<article class="jobTuple">
  <a class="title" href="/job-listing/senior-python-developer-12345">Senior Python Developer</a>
  <a class="subTitle">Acme Corp</a>
  <li class="location">Bangalore</li>
  <li class="salary">₹15-25 LPA</li>
</article>
"""

INDEED_HTML = """
<div class="job_seen_beacon">
  <h2 class="jobTitle"><a class="jcs-JobTitle" href="/rc/clk?jk=abc123">Senior Python Developer</a></h2>
  <span class="companyName">Acme Corp</span>
  <div class="companyLocation">Bangalore, India</div>
</div>
"""


def test_linkedin_parser():
    scraper = LinkedInScraper()
    jobs = scraper._parse_jobs(LINKEDIN_HTML)
    assert len(jobs) == 1
    assert jobs[0].title == "Senior Python Developer"
    assert jobs[0].company == "Acme Corp"
    assert jobs[0].source == "linkedin"


def test_naukri_parser():
    scraper = NaukriScraper()
    jobs = scraper._parse_jobs(NAUKRI_HTML)
    assert len(jobs) == 1
    assert jobs[0].title == "Senior Python Developer"
    assert jobs[0].salary_range == "₹15-25 LPA"
    assert jobs[0].source == "naukri"


def test_indeed_parser():
    scraper = IndeedScraper()
    jobs = scraper._parse_jobs(INDEED_HTML)
    assert len(jobs) == 1
    assert jobs[0].title == "Senior Python Developer"
    assert jobs[0].location == "Bangalore, India"
    assert jobs[0].source == "indeed"
