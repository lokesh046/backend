import os
import httpx
import asyncio
import logging
import base64
from email.message import EmailMessage
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def get_access_token():
    """
    Exchanges the refresh token for a fresh access token.
    """
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip()

    if not all([client_id, client_secret, refresh_token]):
        logger.error("Missing Google OAuth credentials in .env!")
        return None

    url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=payload)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

async def send_email_async(to_email: str, subject: str, html_content: str):
    """
    Asynchronously sends an email using the Gmail API (Port 443, never blocked).
    """
    # 1. Get a fresh access token
    access_token = await get_access_token()
    if not access_token:
        # Fallback to Resend if configured, otherwise fail
        resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
        if resend_api_key:
            logger.info("Falling back to Resend service...")
            return await send_with_resend(to_email, subject, html_content)
        return False

    # 2. Construct the email
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_EMAIL", "lokesh88258@gmail.com")
    msg["To"] = to_email
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    # 3. Encode the message to base64url format required by Gmail API
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    
    # 4. Send via Gmail API
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {"raw": raw_message}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                logger.info(f"SUCCESS: Email sent to {to_email} via Gmail API")
                return True
            else:
                logger.error(f"Gmail API Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Network error while calling Gmail API: {e}")
            return False

async def send_with_resend(to_email: str, subject: str, html_content: str):
    """
    Fallback method using Resend API.
    """
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_email = os.environ.get("FROM_EMAIL", "onboarding@resend.dev").strip()

    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"from": from_email, "to": [to_email], "subject": subject, "html": html_content}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        return response.status_code in [200, 201]

