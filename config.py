import os
from dotenv import load_dotenv

load_dotenv()

# LinkedIn
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")
GOOGLE_TOKEN_PATH = "credentials/google_token.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

# Job Search Filters
JOB_KEYWORDS = [k.strip() for k in os.getenv("JOB_KEYWORDS", "Software Engineer").split(",")]
JOB_LOCATION = os.getenv("JOB_LOCATION", "")
JOB_DATE_FILTER = os.getenv("JOB_DATE_FILTER", "r86400")   # 24 hours
JOB_TYPE = os.getenv("JOB_TYPE", "F")                       # Full-time
JOB_EXPERIENCE = os.getenv("JOB_EXPERIENCE", "")
JOB_REMOTE = os.getenv("JOB_REMOTE", "")
MAX_JOBS_TO_APPLY = int(os.getenv("MAX_JOBS_TO_APPLY", "10"))

# Resume
BASE_RESUME_PATH = os.getenv("BASE_RESUME_PATH", "resumes/base_resume.docx")
YOUR_NAME = os.getenv("YOUR_NAME", "")
YOUR_EMAIL = os.getenv("YOUR_EMAIL", "")
YOUR_PHONE = os.getenv("YOUR_PHONE", "")
YOUR_LOCATION = os.getenv("YOUR_LOCATION", "")
YOUR_LINKEDIN = os.getenv("YOUR_LINKEDIN", "")

# Outputs
OUTPUTS_DIR = "outputs"
RESUMES_DIR = "resumes/tailored"

# LinkedIn URLs
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"

# Date filter map (human-readable labels)
DATE_FILTER_LABELS = {
    "r86400": "Past 24 hours",
    "r604800": "Past week",
    "r2592000": "Past month",
    "": "Any time",
}

# Job type map
JOB_TYPE_LABELS = {
    "F": "Full-time",
    "P": "Part-time",
    "C": "Contract",
    "T": "Temporary",
    "I": "Internship",
    "V": "Volunteer",
    "": "Any",
}

# Experience level map
EXPERIENCE_LABELS = {
    "1": "Internship",
    "2": "Entry level",
    "3": "Associate",
    "4": "Mid-Senior level",
    "5": "Director",
    "6": "Executive",
}
