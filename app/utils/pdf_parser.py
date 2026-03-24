import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text(file_path: str | Path) -> str:
    """Extract plain text from a PDF file using pdfplumber."""
    try:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        logger.error("Failed to extract text from PDF %s: %s", file_path, e)
        raise ValueError(f"Could not parse PDF: {e}") from e
