import logging
import uuid
from datetime import datetime, timezone

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tailored_resume import TailoredResume
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.tailored_resume_repository import TailoredResumeRepository
from app.services.storage_service import StorageService
from app.utils.text_utils import truncate

logger = logging.getLogger(__name__)

TAILOR_PROMPT_TEMPLATE = """\
You are an expert resume writer and career coach. Your task is to tailor the candidate's resume \
to closely match the job description below, maximizing their chances of passing ATS screening \
and impressing human reviewers.

## Job Description
{job_description}

## Candidate's Current Resume
{resume_text}

## Instructions
1. Rewrite the resume to emphasize experiences, skills, and achievements most relevant to the JD.
2. Mirror keywords and terminology used in the JD naturally throughout the resume.
3. Quantify achievements wherever possible (use placeholders like [X%] if exact figures are unknown).
4. Keep the structure professional: Contact Info → Summary → Experience → Skills → Education.
5. Write a 3–4 sentence professional summary tailored specifically to this role.
6. Do NOT fabricate experience or skills the candidate does not have.
7. Output ONLY the tailored resume text — no commentary, no markdown fences, no preamble.

Begin the tailored resume now:
"""


class TailoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.job_repo = JobRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.tailored_repo = TailoredResumeRepository(session)
        self.storage = StorageService()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def tailor(self, job_id: uuid.UUID, resume_id: uuid.UUID) -> TailoredResume:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ValueError(f"Resume not found: {resume_id}")

        if not resume.parsed_text:
            raise ValueError("Resume has no parsed text. Re-upload the PDF.")

        job_description = job.description or f"{job.title} at {job.company}"
        resume_text = resume.parsed_text

        prompt = TAILOR_PROMPT_TEMPLATE.format(
            job_description=truncate(job_description, max_chars=6000),
            resume_text=truncate(resume_text, max_chars=4000),
        )

        # Create a pending record before the API call
        record = await self.tailored_repo.create(
            job_id=job_id,
            resume_id=resume_id,
            prompt_used=prompt,
            model_used=settings.anthropic_model,
            status="pending",
        )

        try:
            response = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            output_text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Persist tailored resume to disk
            output_filename = f"{record.id}.txt"
            await self.storage.save(output_text.encode(), "tailored", output_filename)
            output_path = f"tailored/{output_filename}"

            record = await self.tailored_repo.update(
                record,
                output_text=output_text,
                output_path=output_path,
                tokens_used=tokens_used,
                status="completed",
            )
            logger.info(
                "Tailoring completed: id=%s tokens=%d", record.id, tokens_used
            )

        except Exception as e:
            logger.error("Tailoring failed for job=%s resume=%s: %s", job_id, resume_id, e)
            await self.tailored_repo.update(record, status="failed", error_msg=str(e))
            raise

        return record
