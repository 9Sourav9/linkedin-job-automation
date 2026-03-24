from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.tailored_resume import TailoredResume


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_jobs_source_url", "source_url", unique=True),
        Index("idx_jobs_source", "source"),
        Index("idx_jobs_scraped_at", "scraped_at"),
    )

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    salary_range: Mapped[str | None] = mapped_column(String(200))
    job_type: Mapped[str | None] = mapped_column(String(100))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    raw_html: Mapped[str | None] = mapped_column(Text)

    tailored_resumes: Mapped[list["TailoredResume"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
