from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings


def append_error_log(
    settings: Settings,
    source: str,
    message: str,
    file_name: str | None = None,
    moved_to: str | None = None,
) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "errors.log"
    file_exists = log_file.exists()

    timestamp = datetime.now(timezone.utc).isoformat()
    sanitized_message = message.replace("\n", "\\n")

    with log_file.open("a", encoding="utf-8") as f:
        if not file_exists:
            f.write("# timestamp_utc|source|file_name|moved_to|message\n")
        f.write(
            f"{timestamp}|{source}|{file_name or ''}|{moved_to or ''}|{sanitized_message}\n"
        )


def append_sent_email_log(
    settings: Settings,
    to_email: str,
    subject: str,
    body: str,
    job_language: str | None,
) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "emails_enviados.cvs"
    file_exists = log_file.exists()

    sent_at = datetime.now().astimezone().isoformat(timespec="seconds")
    language_or_type = (job_language or "nao_informado").strip() or "nao_informado"

    with log_file.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer.writerow(
                [
                    "data_envio",
                    "tipo_vaga_ou_linguagem",
                    "titulo",
                    "email",
                    "texto_enviado",
                ]
            )
        writer.writerow([sent_at, language_or_type, subject, to_email, body])
