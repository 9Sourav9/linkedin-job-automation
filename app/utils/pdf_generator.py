"""Generate a professionally formatted resume PDF using Playwright (headless Chromium)."""
import html
import logging
import re

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(
    r"^\s*(SUMMARY|OBJECTIVE|EXPERIENCE|WORK EXPERIENCE|EDUCATION|SKILLS|"
    r"CERTIFICATIONS?|PROJECTS?|ACHIEVEMENTS?|AWARDS?|PUBLICATIONS?|"
    r"LANGUAGES?|INTERESTS?|CONTACT(?: INFO(?:RMATION)?)?|REFERENCES?|VOLUNTEER|HOBBIES?)\s*$",
    re.IGNORECASE,
)

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Calibri', 'Arial', sans-serif;
  font-size: 10pt;
  color: #222;
  line-height: 1.45;
}
.name {
  font-size: 22pt;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.contact {
  font-size: 9pt;
  color: #555;
  margin-bottom: 6px;
}
.top-rule {
  border: none;
  border-top: 1.5px solid #1a1a2e;
  margin: 6px 0 10px;
}
.section-wrap {
  margin-top: 10px;
}
.section-header {
  font-size: 9.5pt;
  font-weight: 700;
  text-transform: uppercase;
  color: #1a1a2e;
  letter-spacing: 0.9px;
  padding-bottom: 3px;
  border-bottom: 0.6px solid #aaa;
  margin-bottom: 5px;
}
.role-line {
  font-size: 9.5pt;
  font-weight: 700;
  color: #1a1a2e;
  margin: 5px 0 2px;
}
.body-line {
  font-size: 9.5pt;
  color: #333;
  margin-bottom: 2px;
}
.bullet {
  font-size: 9.5pt;
  color: #222;
  padding-left: 16px;
  text-indent: -8px;
  margin-bottom: 2px;
}
"""


def _esc(text: str) -> str:
    return html.escape(text)


def _is_section_header(line: str) -> bool:
    return bool(_HEADER_RE.match(line)) or (line.isupper() and 3 < len(line.strip()) < 60)


def _build_resume_html(resume_text: str) -> str:
    """Parse plain-text resume and produce styled HTML."""
    lines = resume_text.splitlines()
    parts = [f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_CSS}</style></head><body>']

    first_content = True
    in_section = False
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # ── Name block ────────────────────────────────────────────────
        if first_content:
            parts.append(f'<div class="name">{_esc(line.strip())}</div>')
            first_content = False
            i += 1
            contact_parts = []
            while i < len(lines):
                cline = lines[i].rstrip()
                if not cline.strip() or _is_section_header(cline):
                    break
                contact_parts.append(_esc(cline.strip()))
                i += 1
            if contact_parts:
                parts.append(f'<div class="contact">{" &nbsp;|&nbsp; ".join(contact_parts)}</div>')
            parts.append('<hr class="top-rule">')
            continue

        # ── Section header ────────────────────────────────────────────
        if _is_section_header(line):
            if in_section:
                parts.append('</div>')
            parts.append(f'<div class="section-wrap"><div class="section-header">{_esc(line.strip().upper())}</div>')
            in_section = True
            i += 1
            continue

        # ── Bullet ────────────────────────────────────────────────────
        if line.lstrip().startswith(("•", "-", "*", "–", "·")):
            clean = re.sub(r"^[\s•\-\*–·]+", "", line)
            parts.append(f'<div class="bullet">• {_esc(clean.strip())}</div>')
            i += 1
            continue

        # ── Role / company line (short line before bullets or blank) ──
        has_sep = bool(re.search(r"\s[\|–—]\s", line))
        next_line = lines[i + 1].rstrip() if i + 1 < len(lines) else ""
        looks_like_role = (
            len(line.strip()) < 100
            and not line.strip().startswith(("http", "(", "["))
            and (
                has_sep
                or not next_line.strip()
                or next_line.lstrip().startswith(("•", "-", "*"))
                or _is_section_header(next_line)
            )
        )
        if looks_like_role:
            parts.append(f'<div class="role-line">{_esc(line.strip())}</div>')
        else:
            parts.append(f'<div class="body-line">{_esc(line.strip())}</div>')

        i += 1

    if in_section:
        parts.append('</div>')
    parts.append('</body></html>')
    return ''.join(parts)


async def generate_resume_pdf(resume_text: str) -> bytes:
    """Render the resume HTML via headless Chromium and return PDF bytes."""
    resume_html = _build_resume_html(resume_text)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(resume_html, wait_until="domcontentloaded")
        pdf_bytes = await page.pdf(
            format="A4",
            margin={"top": "14mm", "bottom": "14mm", "left": "16mm", "right": "16mm"},
            print_background=True,
        )
        await browser.close()

    return pdf_bytes
