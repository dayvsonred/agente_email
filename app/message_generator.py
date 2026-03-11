from __future__ import annotations

import re

from langdetect import LangDetectException, detect
from openai import OpenAI

from app.config import Settings


def detect_language(text: str) -> str:
    if not text.strip():
        return "en"
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def build_email_message(
    settings: Settings,
    job_text: str,
    relevant_cv_points: list[str],
    candidate_name: str,
    preferred_language: str | None = None,
) -> dict:
    language = preferred_language or detect_language(job_text)

    if settings.openai_api_key:
        generated = _generate_with_llm(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            job_text=job_text,
            language=language,
            candidate_name=candidate_name,
            relevant_cv_points=relevant_cv_points,
        )
        if generated:
            generated["used_llm"] = True
            return generated

    subject, body = _fallback_message(language, candidate_name, relevant_cv_points)
    return {
        "detected_language": language,
        "subject": subject,
        "body": body,
        "used_llm": False,
    }


def _generate_with_llm(
    api_key: str,
    model: str,
    job_text: str,
    language: str,
    candidate_name: str,
    relevant_cv_points: list[str],
) -> dict | None:
    client = OpenAI(api_key=api_key)

    points = "\n".join(f"- {point}" for point in relevant_cv_points)
    prompt = (
        "You write concise professional application emails.\n"
        "Return only this format:\n"
        "LANG: <iso_code>\n"
        "SUBJECT: <subject>\n"
        "BODY:\n"
        "<body text>\n\n"
        f"Target language ISO code: {language}\n"
        f"Candidate name: {candidate_name}\n"
        "Relevant CV points:\n"
        f"{points or '- No points available'}\n\n"
        "Job ad OCR text:\n"
        f"{job_text[:7000]}"
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write in the exact requested language and keep email under 220 words."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        text = completion.choices[0].message.content or ""
        return _parse_model_output(text, default_language=language)
    except Exception:
        return None


def _parse_model_output(raw: str, default_language: str) -> dict:
    lang = default_language
    subject = "Application"
    body = raw.strip()

    lang_match = re.search(r"^LANG:\s*(.+)$", raw, flags=re.MULTILINE)
    sub_match = re.search(r"^SUBJECT:\s*(.+)$", raw, flags=re.MULTILINE)
    body_match = re.search(r"^BODY:\s*([\s\S]+)$", raw, flags=re.MULTILINE)

    if lang_match:
        lang = lang_match.group(1).strip().lower()
    if sub_match:
        subject = sub_match.group(1).strip()
    if body_match:
        body = body_match.group(1).strip()

    return {"detected_language": lang, "subject": subject, "body": body}


def _fallback_message(
    language: str,
    candidate_name: str,
    relevant_cv_points: list[str],
) -> tuple[str, str]:
    points_text = "\n".join(f"- {point}" for point in relevant_cv_points[:5])
    if language.startswith("pt"):
        subject = "Candidatura para a vaga"
        body = (
            f"Ola, meu nome e {candidate_name}.\n\n"
            "Tenho interesse na vaga anunciada e acredito ter experiencia relevante:\n"
            f"{points_text or '- Experiencia profissional em areas relacionadas'}\n\n"
            "Fico a disposicao para conversarmos.\n"
            "Obrigado(a)."
        )
        return subject, body

    if language.startswith("es"):
        subject = "Postulacion para la vacante"
        body = (
            f"Hola, mi nombre es {candidate_name}.\n\n"
            "Me interesa la vacante publicada y tengo experiencia relevante:\n"
            f"{points_text or '- Experiencia profesional en areas relacionadas'}\n\n"
            "Quedo a disposicion para conversar.\n"
            "Gracias."
        )
        return subject, body

    subject = "Application for the role"
    body = (
        f"Hello, my name is {candidate_name}.\n\n"
        "I am interested in the advertised role and I believe my experience matches:\n"
        f"{points_text or '- Professional experience in related areas'}\n\n"
        "I would be glad to discuss my profile.\n"
        "Thank you."
    )
    return subject, body
