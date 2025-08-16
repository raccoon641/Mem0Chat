from __future__ import annotations

from typing import Optional

from ..config import get_settings


def send_whatsapp_message(to_phone_e164: str, body: str) -> Optional[str]:
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_number:
        return None
    try:
        from twilio.rest import Client  # Lazy import to avoid import error at app import time

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(
            from_=settings.twilio_whatsapp_number,
            to=to_phone_e164,
            body=body,
        )
        return msg.sid
    except Exception:
        return None 