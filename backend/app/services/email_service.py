"""Service for sending email notifications and confirmation codes.

Provides email-based verification for high-value transactions,
fulfilling the 4.0 grade requirement for an additional user
verification mechanism beyond TOTP 2FA.
"""

import logging
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory store for pending email confirmations
# In production, this should be stored in Redis or the database
_pending_confirmations: Dict[str, dict] = {}


def generate_confirmation_code() -> str:
    """Generate a 6-digit numeric confirmation code."""
    return f"{secrets.randbelow(1000000):06d}"


async def send_confirmation_email(
    to_email: str,
    username: str,
    code: str,
    trade_details: str
) -> bool:
    """Send a transaction confirmation email with a verification code.

    Args:
        to_email: Recipient email address.
        username: Username for personalization.
        code: 6-digit confirmation code.
        trade_details: Human-readable description of the trade.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured – skipping email send (code logged for dev)")
        logger.info(f"[DEV] Email confirmation code for {username}: {code}")
        return True  # Allow operation in dev mode without SMTP

    subject = f"Giełda – Potwierdzenie transakcji #{code}"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f0f19; color: #e0e0e0; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #1a1a2e; border-radius: 12px; padding: 30px; border: 1px solid #2a2a4a;">
            <h2 style="color: #00d4aa; margin-top: 0;">🔐 Potwierdzenie transakcji</h2>
            <p>Witaj <strong>{username}</strong>,</p>
            <p>Otrzymaliśmy żądanie wykonania transakcji o wysokiej wartości:</p>
            <div style="background: #0f0f19; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 3px solid #00d4aa;">
                <code style="color: #00d4aa;">{trade_details}</code>
            </div>
            <p>Twój kod potwierdzenia:</p>
            <div style="text-align: center; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #00d4aa; background: #0f0f19; padding: 15px 30px; border-radius: 8px; display: inline-block;">{code}</span>
            </div>
            <p style="color: #888; font-size: 13px;">Kod jest ważny przez 10 minut. Jeśli nie inicjowałeś tej transakcji, zignoruj tę wiadomość i zmień hasło.</p>
            <hr style="border-color: #2a2a4a;">
            <p style="color: #666; font-size: 11px;">Giełda – Platforma Inwestycyjna</p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        logger.info(f"Confirmation email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {to_email}: {e}")
        return False


def store_pending_confirmation(
    user_id: int,
    code: str,
    trade_data: dict
) -> str:
    """Store a pending trade confirmation and return a confirmation token.

    Args:
        user_id: ID of the user requesting the trade.
        code: The 6-digit confirmation code.
        trade_data: The original trade request data to replay after confirmation.

    Returns:
        A unique confirmation token to reference this pending confirmation.
    """
    token = secrets.token_urlsafe(32)
    _pending_confirmations[token] = {
        "user_id": user_id,
        "code": code,
        "trade_data": trade_data,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
    }

    # Cleanup expired confirmations
    now = datetime.utcnow()
    expired = [k for k, v in _pending_confirmations.items() if v["expires_at"] < now]
    for k in expired:
        del _pending_confirmations[k]

    return token


def verify_confirmation(token: str, code: str, user_id: int) -> Optional[dict]:
    """Verify an email confirmation code and return the original trade data.

    Args:
        token: The confirmation token from store_pending_confirmation.
        code: The 6-digit code the user entered.
        user_id: ID of the current user (must match the stored user_id).

    Returns:
        The original trade_data dict if valid, None otherwise.
    """
    pending = _pending_confirmations.get(token)
    if not pending:
        return None

    if pending["user_id"] != user_id:
        return None

    if datetime.utcnow() > pending["expires_at"]:
        del _pending_confirmations[token]
        return None

    if not secrets.compare_digest(pending["code"], code):
        return None

    # Valid – remove from pending and return trade data
    trade_data = pending["trade_data"]
    del _pending_confirmations[token]
    return trade_data


def requires_email_confirmation(notional_value: float) -> bool:
    """Check if a trade's notional value exceeds the email confirmation threshold.

    Args:
        notional_value: The total USDT value of the trade.

    Returns:
        True if email confirmation is required.
    """
    return notional_value >= settings.EMAIL_CONFIRM_THRESHOLD
