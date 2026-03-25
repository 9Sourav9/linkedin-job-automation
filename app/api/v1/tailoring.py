import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.repositories.tailored_resume_repository import TailoredResumeRepository
from app.services.storage_service import StorageService
from app.schemas.tailored_resume import (
    TailorApplyRequest,
    TailorRequest,
    TailoredResumeListResponse,
    TailoredResumeResponse,
)
from app.services.tailoring_service import TailoringService

router = APIRouter(prefix="/tailor", tags=["tailoring"])


@router.post("", response_model=TailoredResumeResponse, status_code=201, summary="Generate tailoring preview")
async def tailor_resume(
    body: TailorRequest,
    session: AsyncSession = Depends(get_session),
):
    service = TailoringService(session)
    try:
        result = await service.tailor_preview(body.job_id, body.resume_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tailoring failed: {e}")
    return result


@router.post("/{tailored_id}/apply", response_model=TailoredResumeResponse, summary="Apply accepted section changes and generate PDF")
async def apply_tailoring(
    tailored_id: uuid.UUID,
    body: TailorApplyRequest,
    session: AsyncSession = Depends(get_session),
):
    service = TailoringService(session)
    try:
        result = await service.tailor_apply(tailored_id, body.accepted_sections, body.edited_changes, body.full_text_override)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Apply failed: {e}")
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


@router.delete("/{tailored_id}", status_code=204, summary="Delete a tailored resume")
async def delete_tailored(
    tailored_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = TailoredResumeRepository(session)
    record = await repo.get_by_id(tailored_id)
    if not record:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    # Delete the output file if it exists
    if record.output_path:
        storage = StorageService()
        try:
            import os
            os.remove(storage.base_path / record.output_path)
        except FileNotFoundError:
            pass
    await repo.delete(record)


@router.get("/{tailored_id}/download", summary="Download tailored resume as PDF")
async def download_tailored_pdf(
    tailored_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    repo = TailoredResumeRepository(session)
    record = await repo.get_by_id(tailored_id)
    if not record:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    if record.status != "completed" or not record.output_path:
        raise HTTPException(status_code=400, detail="PDF not available yet")

    storage = StorageService()
    try:
        pdf_bytes = await storage.read(record.output_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    is_docx = record.output_path.lower().endswith(".docx")
    if is_docx:
        return Response(
            content=pdf_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="tailored_resume_{tailored_id}.docx"'},
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="tailored_resume_{tailored_id}.pdf"'},
    )


@router.get("/{tailored_id}/download/docx", summary="Download tailored resume as DOCX")
async def download_tailored_docx(
    tailored_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    from app.utils.docx_generator import generate_resume_docx

    repo = TailoredResumeRepository(session)
    record = await repo.get_by_id(tailored_id)
    if not record:
        raise HTTPException(status_code=404, detail="Tailored resume not found")
    if record.status != "completed" or not record.output_text:
        raise HTTPException(status_code=400, detail="Resume not available yet")

    docx_bytes = generate_resume_docx(record.output_text)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="tailored_resume_{tailored_id}.docx"'},
    )
