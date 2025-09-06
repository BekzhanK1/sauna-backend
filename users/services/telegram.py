# app/services/telegram.py
from __future__ import annotations
import logging
import httpx
from django.conf import settings

log = logging.getLogger(__name__)
API_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
STAGE = settings.STAGE

class TelegramError(RuntimeError):
    pass


def _check_config():
    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramError("TELEGRAM_BOT_TOKEN not set")
    if not settings.TELEGRAM_CHAT_ID:
        raise TelegramError("TELEGRAM_CHAT_ID not set")
    if not settings.TELEGRAM_NOTIFICATION_CHAT_ID:
        raise TelegramError("TELEGRAM_NOTIFICATION_CHAT_ID not set")


def send_message(
    text: str,
    chat_id: str | int | None = None,
    parse_mode: str | None = "HTML",
    disable_notification: bool = False,
    chat_type: str | None = "default",
):
    """
    Synchronous helper for standard Django views.
    """
    if STAGE == "DEV":
        return
    _check_config()
    if chat_type == "default":
        cid = chat_id or settings.TELEGRAM_CHAT_ID
    elif chat_type == "notification":
        cid = settings.TELEGRAM_NOTIFICATION_CHAT_ID
    else:
        raise TelegramError("Invalid chat type specified")
    payload = {
        "chat_id": cid,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
    }
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(f"{API_BASE}/sendMessage", json=payload)
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise TelegramError(data)
            return data
    except httpx.HTTPStatusError as e:
        log.error(f"HTTP error occurred: {e.response.text}")
        raise TelegramError(f"HTTP error: {e.response.text}") from e
    except Exception as e:
        log.exception("Failed to send Telegram message")
        raise TelegramError(str(e)) from e
