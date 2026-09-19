import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


def _message_url() -> str:
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    graph_api_version = os.getenv("WHATSAPP_GRAPH_API_VERSION")
    if not phone_number_id or not graph_api_version:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_GRAPH_API_VERSION are required"
        )

    return f"https://graph.facebook.com/{graph_api_version}/{phone_number_id}/messages"


def _send_message(payload: dict[str, Any]) -> None:
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is required")

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = httpx.post(_message_url(), headers=headers, json=payload, timeout=15)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("WhatsApp API request failed")
        raise


def send_text(to: str, message: str) -> None:
    _send_message(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }
    )


def send_claim_button(to: str, offer_id: int, description: str, remaining: int) -> None:
    _send_message(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": (
                        "Leftover food available!\n\n"
                        f"{description}\n"
                        f"{remaining} portions available\n\n"
                        "First come, first served!"
                    )
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"claim:{offer_id}", "title": "CLAIM"},
                        }
                    ]
                },
            },
        }
    )