# Job Automation Platform — Phase 1

Intelligent job aggregation and LLM-powered resume tailoring.

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL running locally
- [Poetry](https://python-poetry.org/docs/) or `pip`

### 2. Install dependencies

```bash
poetry install
# Install Playwright browsers (one-time)
playwright install chromium
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in DATABASE_URL and ANTHROPIC_API_KEY
```

### 4. Create database & run migrations

```bash
# Create the database first
createdb job_automation

# Generate initial migration
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head
```

### 5. Run the server

```bash
uvicorn main:app --reload
```

API docs: http://localhost:8000/docs

---

## Phase 1 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/jobs/scrape` | Trigger job scraping |
| GET | `/api/v1/jobs` | List all stored jobs |
| GET | `/api/v1/jobs/{id}` | Get a single job |
| POST | `/api/v1/resumes` | Upload resume PDF |
| GET | `/api/v1/resumes` | List resumes |
| GET | `/api/v1/resumes/{id}` | Get resume metadata |
| GET | `/api/v1/resumes/{id}/download` | Download original PDF |
| POST | `/api/v1/tailor` | Tailor resume to a job (LLM) |
| GET | `/api/v1/tailor` | List tailored resumes |
| GET | `/api/v1/tailor/{id}` | Get a tailored resume |

---

## Typical Workflow

```bash
# 1. Upload your resume
curl -X POST http://localhost:8000/api/v1/resumes \
  -F "file=@my_resume.pdf" \
  -F "label=Software Engineer Resume"

# 2. Scrape jobs
curl -X POST http://localhost:8000/api/v1/jobs/scrape \
  -H "Content-Type: application/json" \
  -d '{"query": "Python developer", "location": "Bangalore", "sources": ["linkedin", "naukri"], "max_pages": 2}'

# 3. List jobs and pick one
curl http://localhost:8000/api/v1/jobs?limit=10

# 4. Tailor your resume to the job
curl -X POST http://localhost:8000/api/v1/tailor \
  -H "Content-Type: application/json" \
  -d '{"job_id": "<job-uuid>", "resume_id": "<resume-uuid>"}'
```

---

## Running Tests

```bash
pytest tests/unit/ -v
```

---

## Project Structure

```
app/
├── api/v1/         # FastAPI routes (jobs, resumes, tailoring)
├── core/           # Config, DB engine, logging
├── models/         # SQLAlchemy ORM models
├── repositories/   # Async DB access layer
├── schemas/        # Pydantic request/response models
├── scrapers/       # Playwright-based scrapers (LinkedIn, Naukri, Indeed)
├── services/       # Business logic (scraping, resume upload, LLM tailoring)
└── utils/          # PDF parsing, text helpers
```

---

## Roadmap

- **Phase 2**: Email/message generator, resume versioning dashboard
- **Phase 3**: Auto-apply module, full web dashboard
