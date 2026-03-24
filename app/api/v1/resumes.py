import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume import ResumeListResponse, ResumeResponse
from app.services.resume_service import ResumeService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/resumes", tags=["resumes"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("", response_model=ResumeResponse, status_code=201, summary="Upload a resume PDF")
async def upload_resume(
    file: UploadFile = File(...),
    label: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    service = ResumeService(session)
    resume = await service.upload(file_bytes, file.filename, label=label)
    return resume


@router.get("", response_model=ResumeListResponse, summary="List uploaded resumes")
async def list_resumes(
    session: AsyncSession = Depends(get_session),
):
    repo = ResumeRepository(session)
    total, items = await repo.list_active()
    return ResumeListResponse(total=total, items=items)


@router.get("/{resume_id}", response_model=ResumeResponse, summary="Get resume metadata")
async def get_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = ResumeRepository(session)
    resume = await repo.get_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.get("/{resume_id}/download", summary="Download original resume PDF")
async def download_resume(
    resume_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = ResumeRepository(session)
    resume = await repo.get_by_id(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    storage = StorageService()
    try:
        file_bytes = await storage.read(resume.file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{resume.filename}"'},
    )
