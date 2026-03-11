import smtplib
from email.message import EmailMessage

from app.config import Settings


def send_email_smtp(
    settings: Settings,
    to_email: str,
    subject: str,
    body: str,
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
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
