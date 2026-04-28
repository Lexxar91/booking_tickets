import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


def send_email(
    to: str,
    subject: str,
    html: str,
    attachment: bytes | None = None,
    attachment_name: str | None = None,
) -> None:
    """Отправляет email-сообщение."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    mime_type = "mixed" if attachment else "alternative"
    msg = MIMEMultipart(mime_type)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to

    msg.attach(MIMEText(html, "html"))

    if attachment and attachment_name:
        pdf_part = MIMEBase("application", "pdf")
        pdf_part.set_payload(attachment)
        encoders.encode_base64(pdf_part)
        pdf_part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment_name,
        )
        msg.attach(pdf_part)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to, msg.as_string())
