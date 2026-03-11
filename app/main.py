from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

from app.analysis_service import analyze_image_bytes
from app.batch_processor import process_todoist_folder
from app.config import Settings, get_settings
from app.mailer import send_email_smtp
from app.models import AnalyzeResult, BatchProcessResponse, SendEmailRequest, SendEmailResponse


app = FastAPI(title="Job Ad Email Agent", version="1.0.0")


def _auth_guard(
    settings: Settings,
    x_automation_key: str | None,
) -> None:
    if settings.automation_token and x_automation_key != settings.automation_token:
        raise HTTPException(status_code=401, detail="Invalid automation key.")


def _analyze_image(
    image_bytes: bytes,
    settings: Settings,
    candidate_name: str | None = None,
) -> AnalyzeResult:
    try:
        return analyze_image_bytes(
            image_bytes=image_bytes,
            settings=settings,
            candidate_name=candidate_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Analyze error: {exc}") from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResult)
async def analyze(
    image: UploadFile = File(...),
    candidate_name: str | None = Form(default=None),
    x_automation_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResult:
    _auth_guard(settings, x_automation_key)
    image_bytes = await image.read()
    return _analyze_image(image_bytes=image_bytes, settings=settings, candidate_name=candidate_name)


@app.post("/send", response_model=SendEmailResponse)
def send(
    payload: SendEmailRequest,
    x_automation_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> SendEmailResponse:
    _auth_guard(settings, x_automation_key)

    if payload.dry_run:
        return SendEmailResponse(
            sent=False,
            to_email=payload.to_email,
            subject=payload.subject,
            dry_run=True,
        )

    try:
        send_email_smtp(
            settings=settings,
            to_email=str(payload.to_email),
            subject=payload.subject,
            body=payload.body,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Send failed: {exc}") from exc

    return SendEmailResponse(
        sent=True,
        to_email=payload.to_email,
        subject=payload.subject,
        dry_run=False,
    )


@app.post("/process-and-send", response_model=AnalyzeResult)
async def process_and_send(
    image: UploadFile = File(...),
    auto_send: bool = Form(default=False),
    candidate_name: str | None = Form(default=None),
    x_automation_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResult:
    _auth_guard(settings, x_automation_key)

    image_bytes = await image.read()
    result = _analyze_image(image_bytes=image_bytes, settings=settings, candidate_name=candidate_name)

    if auto_send:
        if not result.extracted_email:
            raise HTTPException(status_code=400, detail="No target email was found in the image.")
        try:
            send_email_smtp(
                settings=settings,
                to_email=str(result.extracted_email),
                subject=result.subject,
                body=result.body,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Send failed: {exc}") from exc

    return result


@app.post("/process-todoist", response_model=BatchProcessResponse)
def process_todoist(
    auto_send: bool = Form(default=False),
    candidate_name: str | None = Form(default=None),
    fix_email: str | None = Form(default=None),
    only_email: str | None = Form(default=None),
    x_automation_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> BatchProcessResponse:
    _auth_guard(settings, x_automation_key)
    try:
        return process_todoist_folder(
            settings=settings,
            auto_send=auto_send,
            candidate_name=candidate_name,
            fix_email=fix_email,
            only_email=only_email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {exc}") from exc
