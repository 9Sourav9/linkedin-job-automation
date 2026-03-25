import json
import logging
import re
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

_SECTION_SPLIT_RE = re.compile(
    r"(?m)^[ \t]*(SUMMARY|OBJECTIVE|EXPERIENCE|WORK EXPERIENCE|EDUCATION|SKILLS|"
    r"CERTIFICATIONS?|PROJECTS?|ACHIEVEMENTS?|AWARDS?|PUBLICATIONS?|"
    r"LANGUAGES?|INTERESTS?|CONTACT(?: INFO(?:RMATION)?)?|REFERENCES?|VOLUNTEER|HOBBIES?)[ \t]*$",
    re.IGNORECASE,
)


def _merge_changes_into_original(original_text: str, changes: list[dict]) -> str:
    """Apply accepted (possibly user-edited) section changes onto the original resume text.

    Finds each section's original text verbatim in the original resume and replaces it
    with the tailored (or user-edited) version.
    """
    result = original_text
    for change in changes:
        original = change.get("original", "").strip()
        tailored = change.get("tailored", "").strip()
        if not original or not tailored:
            continue
        if original in result:
            result = result.replace(original, tailored, 1)
        else:
            # Original text not found verbatim — append the tailored section at end
            section = change.get("section", "").strip()
            logger.debug("Section '%s' original not found verbatim; appending tailored text", section)
    return result

# Prompt asks the AI to return a structured JSON diff so the user can
# review each section before the PDF is written.
TAILOR_PROMPT_TEMPLATE = """\
You are an expert resume writer helping a candidate tailor their resume for a specific job.

## Job Description
{job_description}

## Candidate's Current Resume
{resume_text}

## Instructions
1. Read the JD carefully. Identify ONLY the sections that genuinely need modification to better match this specific role.
2. If a section is already well-aligned with the JD, DO NOT include it in "changes" — leave it unchanged.
3. For sections that need changes: return the EXACT original text and the improved tailored text.
4. Mirror keywords and requirements from the JD naturally — do NOT invent skills or experience the candidate doesn't have.
5. CRITICAL — LAYOUT PRESERVATION:
   - The "tailored" text MUST have the EXACT same number of lines as the "original" text.
   - Do NOT add new bullet points or remove existing ones.
   - Do NOT add new sentences or paragraphs.
   - Only REPHRASE the words within each existing line to better match the JD.
   - Each line in "tailored" corresponds 1-to-1 with the same line in "original".
6. The "original" field must be the EXACT verbatim text copied from the resume above.

Return ONLY a valid JSON object — no markdown fences, no extra commentary:
{{
  "changes": [
    {{
      "section": "<SECTION NAME IN CAPS>",
      "original": "<exact verbatim original text — same line count as tailored>",
      "tailored": "<rephrased text — SAME number of lines as original>"
    }}
  ],
  "full_tailored_text": "<complete resume as plain text with only the accepted changes applied>"
}}

If no changes are needed, return: {{"changes": [], "full_tailored_text": "<original resume text unchanged>"}}
"""


class TailoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.job_repo = JobRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.tailored_repo = TailoredResumeRepository(session)
        self.storage = StorageService()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # ------------------------------------------------------------------
    # Step 1: ask AI for proposed changes, store as "preview"
    # ------------------------------------------------------------------
    async def tailor_preview(
        self, job_id: uuid.UUID, resume_id: uuid.UUID
    ) -> TailoredResume:
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ValueError(f"Resume not found: {resume_id}")

        if not resume.parsed_text:
            raise ValueError("Resume has no parsed text. Re-upload the PDF.")

        job_description = job.description or f"{job.title} at {job.company}"

        prompt = TAILOR_PROMPT_TEMPLATE.format(
            job_description=truncate(job_description, max_chars=6000),
            resume_text=truncate(resume.parsed_text, max_chars=4000),
        )

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

            raw = response.content[0].text.strip()
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Parse the JSON — fall back gracefully if the model returns prose
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                # Try to extract JSON block from the text
                import re
                m = re.search(r"\{.*\}", raw, re.DOTALL)
                parsed = json.loads(m.group(0)) if m else {"changes": [], "full_tailored_text": raw}

            record = await self.tailored_repo.update(
                record,
                output_text=json.dumps(parsed),   # JSON stored during preview
                tokens_used=tokens_used,
                status="preview",
            )
            logger.info("Tailor preview ready: id=%s changes=%d", record.id, len(parsed.get("changes", [])))

        except Exception as e:
            logger.error("Tailoring preview failed: %s", e)
            await self.tailored_repo.update(record, status="failed", error_msg=str(e))
            raise

        return record

    # ------------------------------------------------------------------
    # Step 2: user confirmed — apply changes to original PDF
    # ------------------------------------------------------------------
    async def tailor_apply(
        self, tailored_id: uuid.UUID, accepted_sections: list[str] | None = None,
        edited_changes: list[dict] | None = None, full_text_override: str | None = None
    ) -> TailoredResume:
        record = await self.tailored_repo.get_by_id(tailored_id)
        if not record:
            raise ValueError(f"Tailored record not found: {tailored_id}")
        if record.status != "preview":
            raise ValueError(f"Record is not in preview state (status={record.status})")

        resume = await self.resume_repo.get_by_id(record.resume_id)
        if not resume:
            raise ValueError("Original resume not found")

        try:
            parsed = json.loads(record.output_text or "{}")
        except json.JSONDecodeError:
            raise ValueError("Stored preview data is invalid")

        all_changes: list[dict] = parsed.get("changes", [])
        full_text: str = parsed.get("full_tailored_text", "")

        # Filter to only accepted sections if specified
        if accepted_sections is not None:
            accepted_upper = {s.upper() for s in accepted_sections}
            changes = [c for c in all_changes if c.get("section", "").upper() in accepted_upper]
            logger.info("Applying %d/%d accepted sections", len(changes), len(all_changes))
        else:
            changes = all_changes

        # Override tailored text with user-edited versions if provided
        if edited_changes:
            edited_map = {e.get("section", "").upper(): e.get("tailored", "") for e in edited_changes if e.get("section")}
            changes = [
                {**c, "tailored": edited_map[c.get("section", "").upper()]}
                if c.get("section", "").upper() in edited_map else c
                for c in changes
            ]

        from app.utils.docx_editor import apply_section_changes_docx
        from app.utils.docx_generator import generate_resume_docx
        from app.utils.pdf_editor import apply_section_changes
        from app.utils.pdf_generator import generate_resume_pdf

        is_docx = resume.file_path.lower().endswith(".docx")
        original_bytes = await self.storage.read(resume.file_path)

        if is_docx:
            # ── DOCX path ──────────────────────────────────────────────────
            if full_text_override and full_text_override.strip():
                logger.info("DOCX: using full-text override")
                output_bytes = generate_resume_docx(full_text_override.strip())
            elif changes:
                try:
                    output_bytes = apply_section_changes_docx(original_bytes, changes)
                    logger.info("DOCX: applied %d section changes", len(changes))
                except Exception as e:
                    logger.warning("docx_editor failed (%s) — generating fresh DOCX", e)
                    merged = _merge_changes_into_original(resume.parsed_text or full_text or "", changes)
                    output_bytes = generate_resume_docx(merged)
            else:
                output_bytes = generate_resume_docx(full_text or resume.parsed_text or "")

            ext = "docx"
            modified_pdf = output_bytes  # variable reused for storage

        else:
            # ── PDF path ───────────────────────────────────────────────────
            if full_text_override and full_text_override.strip():
                logger.info("PDF: using full-text override")
                modified_pdf = await generate_resume_pdf(full_text_override.strip())
            elif changes:
                try:
                    modified_pdf = apply_section_changes(original_bytes, changes)
                    logger.info("PDF: applied %d section changes via pdf_editor", len(changes))
                except Exception as e:
                    logger.warning("pdf_editor failed (%s) — Playwright fallback", e)
                    merged = _merge_changes_into_original(resume.parsed_text or full_text or "", changes)
                    modified_pdf = await generate_resume_pdf(merged)
            else:
                modified_pdf = await generate_resume_pdf(full_text or resume.parsed_text or "")

            ext = "pdf"

        output_filename = f"{record.id}.{ext}"
        await self.storage.save(modified_pdf, "tailored", output_filename)
        output_path = f"tailored/{output_filename}"

        record = await self.tailored_repo.update(
            record,
            output_text=full_text,         # store plain text after apply
            output_path=output_path,
            status="completed",
        )
        logger.info("Tailor applied: id=%s", record.id)
        return record
