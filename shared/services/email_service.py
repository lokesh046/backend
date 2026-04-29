import os
import smtplib
import asyncio
import logging
from email.message import EmailMessage
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def send_email_async(to_email: str, subject: str, html_content: str):
    """
    Asynchronously sends an email using the built-in smtplib running in a thread.
    """
    smtp_email = os.environ.get("SMTP_EMAIL", "").strip()
    smtp_password = os.environ.get("SMTP_APP_PASSWORD", "").strip()

    if not smtp_email or not smtp_password:
        logger.warning(f"[MOCK EMAIL] To: {to_email} | Subject: {subject}")
        logger.info(f"Content preview: {html_content[:100]}...")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_email
    msg["To"] = to_email
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    def _send():
        # Using a context manager for SMTP ensures it closes properly
        # Added 10s timeout to prevent hanging
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.ehlo() # Identify ourselves to the server
                server.starttls() # Secure the connection
                server.ehlo() # Re-identify after TLS
                server.login(smtp_email, smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"SMTP Error for {to_email}: {e}")
            raise e

    try:
        await asyncio.to_thread(_send)
        logger.info(f"SUCCESS: Email sent to {to_email}")
    except Exception as e:
        logger.error(f"FAILURE: Could not send email to {to_email}. Error: {e}")

