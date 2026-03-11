from pydantic import BaseModel, EmailStr, Field


class AnalyzeResult(BaseModel):
    extracted_email: EmailStr | None = None
    email_candidates: list[str] = Field(default_factory=list)
    detected_language: str
    subject: str
    body: str
    relevant_cv_points: list[str] = Field(default_factory=list)
    ocr_text: str
    used_llm: bool


class SendEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    dry_run: bool = False


class SendEmailResponse(BaseModel):
    sent: bool
    to_email: EmailStr
    subject: str
    dry_run: bool


class BatchFileResult(BaseModel):
    file_name: str
    status: str
    reason: str | None = None
    moved_to: str | None = None
    extracted_email: EmailStr | None = None
    target_email: EmailStr | None = None
    email_source: str | None = None
    sent: bool = False


class BatchProcessResponse(BaseModel):
    scanned_files: int
    processed_new_files: int
    sent_emails: int
    skipped_duplicates: int
    errors: int
    registry_file: str
    done_dir: str
    error_dir: str
    results: list[BatchFileResult] = Field(default_factory=list)
