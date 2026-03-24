# LinkedIn Job Automation

Automates LinkedIn job searching, resume tailoring, and Easy Apply submissions using Claude AI.

## What it does

1. **Scrapes LinkedIn jobs** — searches by keyword, location, date posted, job type, experience level, and remote preference
2. **Creates a Google Doc** — formats all job listings into a shareable Google Doc
3. **Tailors your resume** — uses Claude (claude-opus-4-6) to customize your resume for each job's description
4. **Uploads to Google Drive** — saves each tailored resume to a dedicated Drive folder
5. **Auto-applies** — fills out LinkedIn Easy Apply forms and submits with your tailored resume

---

## Quick Start

```bash
# 1. Run setup (installs dependencies + Playwright browser)
python setup.py

# 2. Fill in your credentials
#    Edit .env (copied from .env.example)

# 3. Add your base resume
#    Place it at: resumes/base_resume.docx

# 4. Set up Google API credentials
#    See: credentials/google_credentials.json

# 5. Test without applying
python main.py --dry-run

# 6. Full auto mode
python main.py
```

---

## Configuration (.env)

| Variable | Description | Example |
|---|---|---|
| `LINKEDIN_EMAIL` | Your LinkedIn email | `you@email.com` |
| `LINKEDIN_PASSWORD` | Your LinkedIn password | `yourpassword` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `GOOGLE_CREDENTIALS_PATH` | Path to Google OAuth JSON | `credentials/google_credentials.json` |
| `JOB_KEYWORDS` | Comma-separated job titles | `Software Engineer,Python Developer` |
| `JOB_LOCATION` | Job location | `San Francisco, CA` |
| `JOB_DATE_FILTER` | Time filter | `r86400` (24h), `r604800` (1 week) |
| `JOB_TYPE` | Job type | `F` (Full-time), `P` (Part-time), `C` (Contract) |
| `JOB_EXPERIENCE` | Experience levels | `2,3` (Entry + Associate) |
| `JOB_REMOTE` | Remote preference | `1` (On-site), `2` (Remote), `3` (Hybrid) |
| `MAX_JOBS_TO_APPLY` | Max applications per run | `10` |
| `BASE_RESUME_PATH` | Your base resume | `resumes/base_resume.docx` |

---

## Command Line Options

```
python main.py [options]

--scrape-only      Only scrape jobs, no resume tailoring or applying
--no-apply         Scrape + create doc + tailor resumes, but don't submit applications
--dry-run          Same as --no-apply (for testing)
--headless         Run browser invisibly (no UI window)
--max-jobs N       Override MAX_JOBS_TO_APPLY from .env
--easy-apply-only  Only process Easy Apply jobs (default: True)
```

---

## Google API Setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable these APIs:
   - **Google Docs API**
   - **Google Drive API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Choose **Desktop app** → Download JSON
6. Save the file as `credentials/google_credentials.json`
7. First run will open a browser to authorize — token saved automatically

---

## Output Files

| File | Description |
|---|---|
| `outputs/jobs.json` | Raw scraped jobs |
| `outputs/jobs_final.json` | Jobs with application statuses |
| `resumes/tailored/resume_*.docx` | Claude-tailored resumes |
| Google Doc | Job listings with clickable links |
| Google Drive folder | All tailored resumes |

---

## Project Structure

```
linkedin_job_auto/
├── main.py                  # Main orchestrator
├── config.py                # Configuration loader
├── setup.py                 # One-time setup script
├── requirements.txt
├── .env.example             # Template for credentials
├── .env                     # Your credentials (git-ignored)
├── modules/
│   ├── linkedin_scraper.py  # Playwright-based LinkedIn scraper
│   ├── resume_tailor.py     # Claude API resume tailoring
│   ├── google_docs.py       # Google Docs/Drive integration
│   └── auto_apply.py        # Easy Apply form automation
├── credentials/             # Google API credentials (git-ignored)
├── resumes/
│   ├── base_resume.docx     # YOUR base resume (you provide this)
│   └── tailored/            # Claude-tailored resumes
└── outputs/                 # JSON logs
```

---

## Important Notes

- **LinkedIn ToS**: Automated scraping and applying may violate LinkedIn's Terms of Service. Use this tool for personal job searching only and at your own risk.
- **2FA/CAPTCHA**: If LinkedIn requires verification, the browser will pause and prompt you to complete it manually.
- **Easy Apply only**: The auto-apply feature only works with LinkedIn's "Easy Apply" button. External applications require manual action.
- **Review before applying**: Use `--dry-run` first to review tailored resumes before mass applying.
- **Rate limiting**: The app adds human-like delays between actions to reduce detection risk.
