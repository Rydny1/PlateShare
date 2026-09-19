import logging
import os

from dotenv import load_dotenv
from twilio.rest import Client


load_dotenv()

logger = logging.getLogger(__name__)


def _client() -> Client:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required")
    return Client(account_sid, auth_token)


def _whatsapp_address(phone: str) -> str:
    if phone.startswith("whatsapp:"):
        return phone
    return f"whatsapp:+{phone.lstrip('+')}"


def _from_address() -> str:
    sender = os.getenv("TWILIO_WHATSAPP_NUMBER")
    if not sender:
        raise RuntimeError("TWILIO_WHATSAPP_NUMBER is required")
    return _whatsapp_address(sender)


def send_text(to: str, message: str) -> None:
    _client().messages.create(
        from_=_from_address(),
        to=_whatsapp_address(to),
        body=message,
    )


def send_claim_message(to: str, offer_id: int, description: str, remaining: int) -> None:
    send_text(
        to,
        "Leftover food available!\n\n"
        f"{description}\n"
        f"{remaining} portions available\n\n"
        f"Reply claim:{offer_id} to claim one portion.\n"
        "First come, first served!",
    )