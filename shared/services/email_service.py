import os
import smtplib
import asyncio
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

async def send_email_async(to_email: str, subject: str, html_content: str):
    """
    Asynchronously sends an email using the built-in smtplib running in a thread.
    """
    smtp_email = os.environ.get("SMTP_EMAIL", "").strip()
    smtp_password = os.environ.get("SMTP_APP_PASSWORD", "").strip()

    if not smtp_email or not smtp_password:
        print(f"⚠️ [MOCK EMAIL] To: {to_email} | Subject: {subject}")
        print(f"Content:\n{html_content}\n")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    def _send():
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)

    try:
        await asyncio.to_thread(_send)
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
