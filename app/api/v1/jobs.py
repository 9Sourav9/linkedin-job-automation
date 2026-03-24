import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobListResponse, JobResponse, JobSearchParams
from app.services.scraper_service import ScraperService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/scrape", summary="Trigger job scraping across sources")
async def scrape_jobs(
    params: JobSearchParams,
    session: AsyncSession = Depends(get_session),
):
    service = ScraperService(session)
    result = await service.run(
        query=params.query,
        location=params.location,
        sources=params.sources,
        max_pages=params.max_pages,
    )
    return result


@router.get("", response_model=JobListResponse, summary="List stored jobs")
async def list_jobs(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    total, items = await repo.list(offset=offset, limit=limit)
    return JobListResponse(total=total, items=items)


@router.get("/{job_id}", response_model=JobResponse, summary="Get a single job")
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
