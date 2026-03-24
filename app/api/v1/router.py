from fastapi import APIRouter

from app.api.v1 import jobs, resumes, tailoring

router = APIRouter()
router.include_router(jobs.router)
router.include_router(resumes.router)
router.include_router(tailoring.router)
