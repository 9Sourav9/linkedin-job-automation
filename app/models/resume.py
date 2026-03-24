from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.tailored_resume import TailoredResume


class Resume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"
    __table_args__ = (Index("idx_resumes_content_hash", "content_hash", unique=True),)

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tailored_resumes: Mapped[list["TailoredResume"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
