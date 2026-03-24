import uuid
from datetime import datetime

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_size: int
    label: str | None = None
    is_active: bool
    parsed_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    total: int
    items: list[ResumeResponse]
