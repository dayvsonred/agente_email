import base64
import json
import smtplib
from email.message import EmailMessage
from urllib import error, parse, request

from app.config import Settings
from app.log_store import append_sent_email_log


def send_email_smtp(
    settings: Settings,
    to_email: str,
    subject: str,
    body: str,
    job_language: str | None = None,
) -> None:
    if not settings.smtp_host:
        raise ValueError("SMTP_HOST is not configured.")

    from_email = settings.from_email or settings.smtp_username
    if not from_email:
        raise ValueError("FROM_EMAIL or SMTP_USERNAME must be configured.")

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.ehlo()
        if settings.smtp_use_tls:
            server.starttls()
            server.ehlo()

        _authenticate_smtp(
            server=server,
            settings=settings,
            from_email=from_email,
        )

        server.send_message(msg)
    _append_send_log_csv(
        settings=settings,
        to_email=to_email,
        subject=subject,
        body=body,
        job_language=job_language,
    )


def _authenticate_smtp(
    server: smtplib.SMTP,
    settings: Settings,
    from_email: str,
) -> None:
    auth_mode = (settings.smtp_auth_mode or "password").strip().lower()

    if auth_mode == "password":
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
            return
        if settings.smtp_username or settings.smtp_password:
            raise ValueError(
                "SMTP_AUTH_MODE=password requires both SMTP_USERNAME and SMTP_PASSWORD."
            )
        return

    if auth_mode == "gmail_oauth2":
        oauth_user = settings.smtp_username or from_email
        if not oauth_user:
            raise ValueError(
                "SMTP_USERNAME or FROM_EMAIL must be configured for Gmail OAuth2 authentication."
            )
        access_token = _get_gmail_oauth2_access_token(settings)
        _smtp_auth_xoauth2(server=server, user=oauth_user, access_token=access_token)
        return

    raise ValueError(
        "SMTP_AUTH_MODE is invalid. Use 'password' or 'gmail_oauth2'."
    )


def _get_gmail_oauth2_access_token(settings: Settings) -> str:
    if settings.gmail_oauth2_access_token:
        token = settings.gmail_oauth2_access_token.strip()
        if token:
            return token

    missing = [
        key
        for key, value in [
            ("GMAIL_OAUTH2_CLIENT_ID", settings.gmail_oauth2_client_id),
            ("GMAIL_OAUTH2_CLIENT_SECRET", settings.gmail_oauth2_client_secret),
            ("GMAIL_OAUTH2_REFRESH_TOKEN", settings.gmail_oauth2_refresh_token),
        ]
        if not value
    ]
    if missing:
        raise ValueError(
            "Missing Gmail OAuth2 configuration: " + ", ".join(missing)
        )

    data = parse.urlencode(
        {
            "client_id": settings.gmail_oauth2_client_id,
            "client_secret": settings.gmail_oauth2_client_secret,
            "refresh_token": settings.gmail_oauth2_refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = request.Request(
        settings.gmail_oauth2_token_uri,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as resp:
            payload = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(
            f"Gmail OAuth2 token request failed with HTTP {exc.code}: {detail}"
        ) from exc
    except error.URLError as exc:
        raise ValueError(f"Gmail OAuth2 token request failed: {exc.reason}") from exc

    try:
        token_response = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON from Gmail OAuth2 token endpoint.") from exc

    access_token = token_response.get("access_token")
    if not access_token:
        raise ValueError("Gmail OAuth2 token endpoint did not return access_token.")
    return str(access_token)


def _smtp_auth_xoauth2(
    server: smtplib.SMTP,
    user: str,
    access_token: str,
) -> None:
    auth_string = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
    encoded = base64.b64encode(auth_string.encode("utf-8")).decode("ascii")
    code, response = server.docmd("AUTH", f"XOAUTH2 {encoded}")
    if code != 235:
        if isinstance(response, bytes):
            message = response.decode("utf-8", errors="replace")
        else:
            message = str(response)
        raise ValueError(f"Gmail OAuth2 SMTP auth failed ({code}): {message}")


def _append_send_log_csv(
    settings: Settings,
    to_email: str,
    subject: str,
    body: str,
    job_language: str | None,
) -> None:
    append_sent_email_log(
        settings=settings,
        to_email=to_email,
        subject=subject,
        body=body,
        job_language=job_language,
    )
