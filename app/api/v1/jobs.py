import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobListResponse, JobResponse, JobSearchParams
from app.services.scraper_service import ScraperService


class AppliedUpdate(BaseModel):
    applied: bool

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


@router.patch("/{job_id}/applied", response_model=JobResponse, summary="Mark job as applied / not applied")
async def update_applied(
    job_id: uuid.UUID,
    body: AppliedUpdate,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.mark_applied(job_id, body.applied)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=204, summary="Delete a job")
async def delete_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await repo.delete(job)
    return None


@router.post("/{job_id}/delete", status_code=204, summary="Delete a job (POST fallback)")
async def delete_job_post(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = JobRepository(session)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await repo.delete(job)
    return None
