import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class JobBase(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    salary_range: str | None = None
    job_type: str | None = None
    source: str
    source_url: str


class JobCreate(JobBase):
    posted_at: datetime | None = None
    scraped_at: datetime
    raw_html: str | None = None


class JobResponse(JobBase):
    id: uuid.UUID
    posted_at: datetime | None = None
    scraped_at: datetime
    is_active: bool
    applied: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    total: int
    items: list[JobResponse]


class JobSearchParams(BaseModel):
    query: str
    location: str = ""
    sources: list[str] = ["linkedin", "naukri", "indeed"]
    max_pages: int = 3
