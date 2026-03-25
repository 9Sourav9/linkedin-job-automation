"""
Edit a resume PDF by replacing text line-by-line using PyMuPDF.

Strategy:
  1. Split original + tailored into paired lines.
  2. Find each original line in the PDF using multiple search strategies.
  3. Draw white rect over it, insert new line at same position with same font.
"""
import logging
import re
import unicodedata

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ── Font helpers ───────────────────────────────────────────────────────────────

def _pick_base14_font(pdf_font_name: str) -> str:
    n = pdf_font_name.lower()
    is_bold   = any(w in n for w in ("bold", "black", "heavy", "demi", "semibold"))
    is_italic = any(w in n for w in ("italic", "oblique"))
    is_serif  = any(w in n for w in ("times", "georgia", "garamond", "palatino"))
    is_mono   = any(w in n for w in ("courier", "mono", "consol", "typewriter"))
    if is_mono:   return "cobo" if is_bold else "cour"
    if is_serif:
        if is_bold and is_italic: return "tibi"
        if is_bold:               return "tibo"
        if is_italic:             return "tiit"
        return "tiro"
    if is_bold:   return "hebo"
    if is_italic: return "heit"
    return "helv"


def _color_from_int(c: int):
    return ((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0, (c & 0xFF) / 255.0


def _get_font_at_rect(page: fitz.Page, rect: fitz.Rect) -> dict:
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if fitz.Rect(span["bbox"]).intersects(rect):
                    return {
                        "font":  span.get("font", "Helvetica"),
                        "size":  span.get("size", 10.0),
                        "color": _color_from_int(span.get("color", 0)),
                    }
    return {"font": "helv", "size": 10.0, "color": (0.0, 0.0, 0.0)}


def _try_embed_font(doc: fitz.Document, page: fitz.Page, pdf_font_name: str):
    for xref, _ext, _type, name, _enc, _ref in page.get_fonts(full=True):
        if not name:
            continue
        a = name.lower().replace("-", "").replace(" ", "")
        b = pdf_font_name.lower().replace("-", "").replace(" ", "")
        if a in b or b in a:
            try:
                data = doc.extract_font(xref)
                buf = data[3] if data else None
                if buf and len(buf) > 200:
                    alias = f"emb{xref}"
                    page.insert_font(fontname=alias, fontbuffer=buf)
                    return alias
            except Exception:
                pass
    return None


# ── Text normalisation ─────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Normalise unicode, collapse whitespace."""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── Robust line finder ─────────────────────────────────────────────────────────

def _find_rect_for_line(page: fitz.Page, text: str):
    """
    Try several strategies to locate `text` on the page.
    Returns fitz.Rect or None.
    """
    text = text.strip()
    if not text or len(text) < 4:
        return None

    # Strategy 1: exact search
    hits = page.search_for(text)
    if hits:
        logger.debug("Found (exact): '%s'", text[:60])
        return fitz.Rect(hits[0])

    # Strategy 2: normalised text (handles ligatures, fancy spaces)
    normed = _norm(text)
    if normed != text:
        hits = page.search_for(normed)
        if hits:
            logger.debug("Found (normed): '%s'", normed[:60])
            return fitz.Rect(hits[0])

    # Strategy 3: search on leading distinctive substring (first 35 chars)
    if len(text) > 20:
        partial = text[:35].rstrip()
        hits = page.search_for(partial)
        if hits:
            logger.debug("Found (partial): '%s'", partial)
            return fitz.Rect(hits[0])

    # Strategy 4: match via get_text("dict") spans — fuzzy word overlap
    words_needle = set(_norm(text).lower().split())
    if len(words_needle) >= 3:
        best_rect = None
        best_score = 0
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = _norm(" ".join(s.get("text", "") for s in spans)).lower()
                words_line = set(line_text.split())
                score = len(words_needle & words_line) / max(len(words_needle), 1)
                if score > 0.7 and score > best_score:
                    best_score = score
                    best_rect = fitz.Rect(line["bbox"])
        if best_rect:
            logger.debug("Found (fuzzy %.0f%%): '%s'", best_score * 100, text[:60])
            return best_rect

    logger.debug("NOT FOUND: '%s'", text[:60])
    return None


# ── Single-line replacement ─────────────────────────────────────────────────────

def _replace_line(doc: fitz.Document, page: fitz.Page,
                  orig_line: str, new_line: str) -> bool:
    rect = _find_rect_for_line(page, orig_line)
    if rect is None:
        return False

    info      = _get_font_at_rect(page, rect)
    font_size = info["size"]
    color     = info["color"]
    fontname  = _try_embed_font(doc, page, info["font"]) or _pick_base14_font(info["font"])

    # White-box the original line
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

    # Insert new text at the same baseline
    baseline = fitz.Point(rect.x0, rect.y0 + font_size * 0.82)
    page.insert_text(
        baseline,
        new_line.strip(),
        fontname=fontname,
        fontsize=font_size,
        color=color,
        overlay=True,
    )
    return True


# ── Public API ─────────────────────────────────────────────────────────────────

def apply_section_changes(pdf_bytes: bytes, changes: list[dict]) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    total_replaced = 0

    for change in changes:
        original = change.get("original", "")
        tailored = change.get("tailored", "")
        section  = change.get("section", "?")

        if not original.strip() or not tailored.strip():
            continue

        orig_lines = [l for l in original.splitlines() if l.strip()]
        new_lines  = [l for l in tailored.splitlines() if l.strip()]

        replaced_count = 0
        for orig_line, new_line in zip(orig_lines, new_lines):
            if _norm(orig_line) == _norm(new_line):
                continue  # identical — skip

            for page in doc:
                if _replace_line(doc, page, orig_line, new_line):
                    replaced_count += 1
                    break

        total_replaced += replaced_count
        logger.info("pdf_editor: section '%s' — %d/%d lines replaced",
                    section, replaced_count, len(orig_lines))

    if total_replaced == 0:
        logger.warning("pdf_editor: NO lines were replaced — raising so fallback triggers")
        raise RuntimeError("pdf_editor could not locate any text to replace")

    return doc.tobytes(garbage=4, deflate=True)
