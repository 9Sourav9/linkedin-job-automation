import hashlib
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository
from app.services.storage_service import StorageService
from app.utils import pdf_parser

logger = logging.getLogger(__name__)


class ResumeService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ResumeRepository(session)
        self.storage = StorageService()

    async def upload(
        self, file_bytes: bytes, filename: str, label: str | None = None
    ) -> Resume:
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # Reject exact duplicates
        existing = await self.repo.get_by_hash(content_hash)
        if existing:
            logger.info("Resume already exists (hash match): %s", existing.id)
            return existing

        # Save to disk
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        saved_path = await self.storage.save(file_bytes, "resumes", unique_name)
        relative = self.storage.relative_path(saved_path)

        # Extract text
        try:
            parsed_text = pdf_parser.extract_text(saved_path)
        except ValueError as e:
            logger.warning("Could not parse PDF text: %s", e)
            parsed_text = None

        resume = await self.repo.create(
            filename=filename,
            file_path=relative,
            file_size=len(file_bytes),
            content_hash=content_hash,
            parsed_text=parsed_text,
            label=label,
            is_active=True,
        )
        logger.info("Resume uploaded: id=%s filename=%s", resume.id, filename)
        return resume
