from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.naukri import NaukriScraper
from app.scrapers.indeed import IndeedScraper

SCRAPERS = {
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "indeed": IndeedScraper,
}
