from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import shutil

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.analysis_service import analyze_image_bytes
from app.config import Settings
from app.log_store import append_error_log
from app.mailer import send_email_smtp
from app.models import BatchFileResult, BatchProcessResponse


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
EMAIL_ADAPTER = TypeAdapter(EmailStr)


def process_todoist_folder(
    settings: Settings,
    auto_send: bool = False,
    candidate_name: str | None = None,
    fix_email: str | None = None,
    only_email: str | None = None,
) -> BatchProcessResponse:
    todoist_dir = Path(settings.todoist_dir)
    done_dir = Path(settings.done_dir)
    error_dir = Path(settings.error_send_dir)
    registry_file = Path(settings.processed_registry_file)

    normalized_fix_email = _normalize_email(fix_email) if fix_email else None
    normalized_only_email = _normalize_email(only_email) if only_email else None

    todoist_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)
    error_dir.mkdir(parents=True, exist_ok=True)
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    _ensure_registry_header(registry_file)

    already_processed = _load_processed_hashes(registry_file)
    input_files = sorted(
        [p for p in todoist_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda p: p.stat().st_mtime,
    )

    results: list[BatchFileResult] = []
    processed_new_files = 0
    sent_emails = 0
    skipped_duplicates = 0
    errors = 0

    for file_path in input_files:
        file_hash = _sha256_of_file(file_path)

        if file_hash in already_processed:
            moved_to = _move_with_collision(file_path, done_dir)
            skipped_duplicates += 1
            results.append(
                BatchFileResult(
                    file_name=file_path.name,
                    status="skipped",
                    reason="already_processed",
                    moved_to=str(moved_to),
                    sent=False,
                )
            )
            continue

        try:
            image_bytes = file_path.read_bytes()
            analyzed = analyze_image_bytes(
                image_bytes=image_bytes,
                settings=settings,
                candidate_name=candidate_name,
            )

            target_email, email_source = _resolve_target_email(
                extracted_email=str(analyzed.extracted_email) if analyzed.extracted_email else None,
                fix_email=normalized_fix_email,
                only_email=normalized_only_email,
            )
            if not target_email:
                errors += 1
                moved_to = _move_with_collision(file_path, error_dir)
                append_error_log(
                    settings=settings,
                    source="process_todoist_folder",
                    message="no_email_found_in_image",
                    file_name=file_path.name,
                    moved_to=str(moved_to),
                )
                _append_registry_entry(
                    registry_file=registry_file,
                    file_hash=file_hash,
                    file_name=file_path.name,
                    status="error_no_email",
                    extracted_email=str(analyzed.extracted_email or ""),
                    target_email="",
                    email_source="",
                    moved_to=str(moved_to),
                    sent=False,
                )
                results.append(
                    BatchFileResult(
                        file_name=file_path.name,
                        status="error",
                        reason="no_email_found_in_image",
                        moved_to=str(moved_to),
                        extracted_email=analyzed.extracted_email,
                        sent=False,
                    )
                )
                continue

            sent = False
            if auto_send:
                send_email_smtp(
                    settings=settings,
                    to_email=target_email,
                    subject=analyzed.subject,
                    body=analyzed.body,
                    job_language=analyzed.detected_language,
                )
                sent = True
                sent_emails += 1

            moved_to = _move_with_collision(file_path, done_dir)
            processed_new_files += 1
            _append_registry_entry(
                registry_file=registry_file,
                file_hash=file_hash,
                file_name=file_path.name,
                status="processed",
                extracted_email=str(analyzed.extracted_email or ""),
                target_email=target_email,
                email_source=email_source or "",
                moved_to=str(moved_to),
                sent=sent,
            )
            already_processed.add(file_hash)

            results.append(
                BatchFileResult(
                    file_name=file_path.name,
                    status="processed",
                    moved_to=str(moved_to),
                    extracted_email=analyzed.extracted_email,
                    target_email=target_email,
                    email_source=email_source,
                    sent=sent,
                )
            )
        except Exception as exc:
            errors += 1
            moved_to = None
            if file_path.exists():
                moved_to = _move_with_collision(file_path, error_dir)
            append_error_log(
                settings=settings,
                source="process_todoist_folder",
                message=str(exc),
                file_name=file_path.name,
                moved_to=str(moved_to) if moved_to else None,
            )
            _append_registry_entry(
                registry_file=registry_file,
                file_hash=file_hash,
                file_name=file_path.name,
                status="error",
                extracted_email="",
                target_email="",
                email_source="",
                moved_to=str(moved_to) if moved_to else "",
                sent=False,
            )
            results.append(
                BatchFileResult(
                    file_name=file_path.name,
                    status="error",
                    reason=str(exc),
                    moved_to=str(moved_to) if moved_to else None,
                    sent=False,
                )
            )

    return BatchProcessResponse(
        scanned_files=len(input_files),
        processed_new_files=processed_new_files,
        sent_emails=sent_emails,
        skipped_duplicates=skipped_duplicates,
        errors=errors,
        registry_file=str(registry_file),
        done_dir=str(done_dir),
        error_dir=str(error_dir),
        results=results,
    )


def _resolve_target_email(
    extracted_email: str | None,
    fix_email: str | None,
    only_email: str | None,
) -> tuple[str | None, str | None]:
    if only_email:
        return only_email, "only_email"
    if extracted_email:
        return extracted_email, "image"
    if fix_email:
        return fix_email, "fix_email"
    return None, None


def _normalize_email(email: str) -> str:
    value = email.strip().lower()
    try:
        normalized = EMAIL_ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise ValueError(f"Invalid email value: {email}") from exc
    return str(normalized)


def _sha256_of_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _load_processed_hashes(registry_file: Path) -> set[str]:
    seen: set[str] = set()
    if not registry_file.exists():
        return seen

    for line in registry_file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        status = parts[3].strip().lower()
        if status == "processed":
            seen.add(parts[1].strip())
    return seen


def _ensure_registry_header(registry_file: Path) -> None:
    if registry_file.exists():
        return
    header = (
        "# processed_at_utc|sha256|file_name|status|"
        "extracted_email|target_email|email_source|sent|moved_to\n"
    )
    registry_file.write_text(header, encoding="utf-8")


def _append_registry_entry(
    registry_file: Path,
    file_hash: str,
    file_name: str,
    status: str,
    extracted_email: str,
    target_email: str,
    email_source: str,
    moved_to: str,
    sent: bool,
) -> None:
    processed_at = datetime.now(timezone.utc).isoformat()
    line = (
        f"{processed_at}|{file_hash}|{file_name}|{status}|{extracted_email}|"
        f"{target_email}|{email_source}|{str(sent).lower()}|{moved_to}\n"
    )
    with registry_file.open("a", encoding="utf-8") as file:
        file.write(line)


def _move_with_collision(source: Path, target_dir: Path) -> Path:
    destination = target_dir / source.name
    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = target_dir / f"{source.stem}_{timestamp}{source.suffix}"
    shutil.move(str(source), str(destination))
    return destination
