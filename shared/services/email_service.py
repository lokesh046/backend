import os
import httpx
import asyncio
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def send_email_async(to_email: str, subject: str, html_content: str):
    """
    Asynchronously sends an email using Resend's HTTP API (bypasses SMTP port blocks).
    """
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    # Default 'From' address for Resend onboarding is 'onboarding@resend.dev'
    # Once you verify a domain, you can change this to 'support@yourdomain.com'
    from_email = os.environ.get("FROM_EMAIL", "onboarding@resend.dev").strip()

    if not api_key:
        logger.warning(f"[MOCK EMAIL] To: {to_email} | Subject: {subject}")
        logger.info(f"Content preview: {html_content[:100]}...")
        logger.error("RESEND_API_KEY is missing! Please add it to your environment variables.")
        return

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    async def _send():
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code in [200, 201]:
                    logger.info(f"SUCCESS: Email sent to {to_email} via Resend")
                    return True
                else:
                    logger.error(f"Resend API Error: {response.status_code} - {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Network error while calling Resend: {e}")
                return False

    # Since we are already using an async client, we can just await it
    await _send()

