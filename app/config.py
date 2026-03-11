from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    from_email: str | None = Field(default=None, alias="FROM_EMAIL")

    cv_file: Path = Field(default=Path("data/cv.txt"), alias="CV_FILE")
    cv_file_pt: Path = Field(default=Path("data/cv-pt.txt"), alias="CV_FILE_PT")
    cv_file_en: Path = Field(default=Path("data/CV-en.txt"), alias="CV_FILE_EN")
    todoist_dir: Path = Field(default=Path("data/todoist"), alias="TODOIST_DIR")
    done_dir: Path = Field(default=Path("data/done"), alias="DONE_DIR")
    error_send_dir: Path = Field(default=Path("data/errosend"), alias="ERRORSEND_DIR")
    processed_registry_file: Path = Field(
        default=Path("data/processed_files.txt"),
        alias="PROCESSED_REGISTRY_FILE",
    )
    candidate_name: str = Field(default="Candidate", alias="CANDIDATE_NAME")
    automation_token: str | None = Field(default=None, alias="AUTOMATION_TOKEN")
    tesseract_cmd: str | None = Field(default=None, alias="TESSERACT_CMD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
