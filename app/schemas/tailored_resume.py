import uuid
from datetime import datetime

from pydantic import BaseModel


class TailorRequest(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID


class TailoredResumeResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    model_used: str
    output_text: str | None = None
    output_path: str | None = None
    tokens_used: int | None = None
    status: str
    error_msg: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TailoredResumeListResponse(BaseModel):
    total: int
    items: list[TailoredResumeResponse]
