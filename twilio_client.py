import logging
import json
import os
from urllib.parse import quote

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


def send_claim_message(
    to: str,
    offer_id: int,
    description: str,
    remaining: int,
    claim_url: str | None = None,
    media_url: str | None = None,
) -> None:
    content_sid = os.getenv("TWILIO_OFFER_CONTENT_SID")
    if content_sid and claim_url:
        _client().messages.create(
            from_=_from_address(),
            to=_whatsapp_address(to),
            content_sid=content_sid,
            content_variables=json.dumps(
                {
                    "1": description,
                    "2": str(remaining),
                    "3": claim_url,
                }
            ),
        )
        return

    button_text = f"\n\nClaim here: {claim_url}" if claim_url else ""
    client = _client()
    message_args = {
        "from_": _from_address(),
        "to": _whatsapp_address(to),
        "body": (
            "Leftover food available!\n\n"
            f"{description}\n"
            f"{remaining} portions available\n\n"
            f"Reply claim:{offer_id} to claim one portion."
            f"{button_text}\n"
            "First come, first served!"
        ),
    }
    if media_url:
        message_args["media_url"] = [media_url]
    client.messages.create(**message_args)