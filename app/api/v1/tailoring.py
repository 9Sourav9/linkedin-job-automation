import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.repositories.tailored_resume_repository import TailoredResumeRepository
from app.schemas.tailored_resume import (
    TailorRequest,
    TailoredResumeListResponse,
    TailoredResumeResponse,
)
from app.services.tailoring_service import TailoringService

router = APIRouter(prefix="/tailor", tags=["tailoring"])


@router.post("", response_model=TailoredResumeResponse, status_code=201, summary="Tailor resume to a job")
async def tailor_resume(
    body: TailorRequest,
    session: AsyncSession = Depends(get_session),
):
    service = TailoringService(session)
    try:
        result = await service.tailor(body.job_id, body.resume_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tailoring failed: {e}")
    return result


@router.get("", response_model=TailoredResumeListResponse, summary="List tailored resumes")
async def list_tailored(
    job_id: uuid.UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    repo = TailoredResumeRepository(session)
    if job_id:
        total, items = await repo.list_by_job(job_id, offset=offset, limit=limit)
    else:
        total, items = await repo.list(offset=offset, limit=limit)
    return TailoredResumeListResponse(total=total, items=items)


@router.get("/{tailored_id}", response_model=TailoredResumeResponse, summary="Get a tailored resume")
async def get_tailored(
    tailored_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = TailoredResumeRepository(session)
    record = await repo.get_by_id(tailored_id)
    if not record:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    return record
