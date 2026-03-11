import re
from pathlib import Path


STOPWORDS = {
    "about",
    "with",
    "from",
    "this",
    "that",
    "have",
    "para",
    "com",
    "uma",
    "por",
    "sobre",
    "vaga",
    "job",
    "the",
    "and",
    "you",
    "your",
    "dos",
    "das",
    "uma",
    "de",
    "da",
    "do",
    "em",
    "que",
    "para",
}


def load_cv_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"CV file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def select_relevant_cv_points(cv_text: str, job_text: str, limit: int = 8) -> list[str]:
    lines = [line.strip("- ").strip() for line in cv_text.splitlines() if line.strip()]
    if not lines:
        return []

    keywords = _extract_keywords(job_text)
    if not keywords:
        return lines[:limit]

    scored = []
    for line in lines:
        words = set(_extract_keywords(line))
        score = len(words.intersection(keywords))
        scored.append((score, line))

    scored.sort(key=lambda item: item[0], reverse=True)
    best = [line for score, line in scored if score > 0][:limit]
    return best or lines[:limit]


def _extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9+#]{4,}", text.lower())
    return [word for word in words if word not in STOPWORDS]
