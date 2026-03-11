from pathlib import Path

from app.config import Settings
from app.cv_matcher import load_cv_text, select_relevant_cv_points
from app.message_generator import build_email_message, detect_language
from app.models import AnalyzeResult
from app.ocr import extract_email_candidates, extract_text_from_image_bytes, pick_best_email


def resolve_cv_path(settings: Settings, detected_language: str) -> Path:
    if detected_language.startswith("pt"):
        candidates = [settings.cv_file_pt, settings.cv_file]
    elif detected_language.startswith("en"):
        candidates = [settings.cv_file_en, settings.cv_file]
    else:
        candidates = [settings.cv_file]

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return path
    return Path(settings.cv_file)


def analyze_image_bytes(
    image_bytes: bytes,
    settings: Settings,
    candidate_name: str | None = None,
) -> AnalyzeResult:
    ocr_text = extract_text_from_image_bytes(
        image_bytes=image_bytes,
        tesseract_cmd=settings.tesseract_cmd,
    )
    email_candidates = extract_email_candidates(ocr_text)
    extracted_email = pick_best_email(email_candidates)

    detected_language = detect_language(ocr_text)
    selected_cv_path = resolve_cv_path(settings, detected_language)
    cv_text = load_cv_text(selected_cv_path)
    relevant_points = select_relevant_cv_points(cv_text, ocr_text)

    message = build_email_message(
        settings=settings,
        job_text=ocr_text,
        relevant_cv_points=relevant_points,
        candidate_name=candidate_name or settings.candidate_name,
        preferred_language=detected_language,
    )

    return AnalyzeResult(
        extracted_email=extracted_email,
        email_candidates=email_candidates,
        detected_language=message["detected_language"],
        subject=message["subject"],
        body=message["body"],
        relevant_cv_points=relevant_points,
        ocr_text=ocr_text,
        used_llm=message["used_llm"],
    )
