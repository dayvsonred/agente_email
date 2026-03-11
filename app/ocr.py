import io
import re
from typing import Iterable

from PIL import Image
import pytesseract


EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_text_from_image_bytes(image_bytes: bytes, tesseract_cmd: str | None = None) -> str:
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return pytesseract.image_to_string(image).strip()


def extract_email_candidates(text: str) -> list[str]:
    found = EMAIL_REGEX.findall(text or "")
    return _unique_preserve_order(email.lower() for email in found)


def pick_best_email(candidates: list[str]) -> str | None:
    if not candidates:
        return None

    no_reply_markers = ("noreply", "no-reply", "do-not-reply")
    for email in candidates:
        if not any(marker in email for marker in no_reply_markers):
            return email
    return candidates[0]


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
