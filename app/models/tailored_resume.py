import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.job import Job
from app.models.resume import Resume


class TailoredResume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tailored_resumes"
    __table_args__ = (
        Index("idx_tr_job_id", "job_id"),
        Index("idx_tr_resume_id", "resume_id"),
        Index("idx_tr_status", "status"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(Text)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    error_msg: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="tailored_resumes")
    resume: Mapped[Resume] = relationship(back_populates="tailored_resumes")
