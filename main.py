import logging
import os
import re
from contextlib import asynccontextmanager
from html import escape
from typing import Any

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import create_tables
from database import get_db
from models import Claim, Offer, Staff, Student
from whatsapp import send_claim_button, send_text


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(title="PlateShare Cafeteria Bot", lifespan=lifespan)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def safe_send_text(to: str, message: str) -> None:
    try:
        send_text(to, message)
    except Exception:
        logger.exception("Could not send WhatsApp response")


def safe_send_claim_button(to: str, offer: Offer) -> None:
    try:
        send_claim_button(to, offer.id, offer.description, offer.remaining_quantity)
    except Exception:
        logger.exception("Could not send offer notification")


def registration_help() -> str:
    return (
        "Welcome!\n\n"
        "You are not registered yet.\n\n"
        "Student:\nSend /register Your Name\n\n"
        "Cafeteria staff:\nSend /staff Your Name"
    )


def get_message_details(payload: dict[str, Any]) -> tuple[str, str] | None:
    try:
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = normalize_phone(message["from"])
    except (KeyError, IndexError, TypeError):
        return None

    if message.get("type") == "text":
        body = message.get("text", {}).get("body", "")
    elif message.get("type") == "interactive":
        interactive = message.get("interactive", {})
        button_reply = interactive.get("button_reply", {})
        body = button_reply.get("id", "")
    else:
        body = ""

    return sender, body.strip()


def handle_register(db: Session, phone: str, name: str, as_staff: bool) -> str:
    model = Staff if as_staff else Student
    existing = db.scalar(select(model).where(model.phone_nr == phone))
    role_name = "staff" if as_staff else "student"
    if existing:
        return f"You're already registered as {role_name}."

    user = model(name=name, phone_nr=phone)
    db.add(user)
    db.commit()
    logger.info("Registered %s user %s", role_name, phone[-4:])
    return f"You're registered as a {role_name}, {name}!"


def format_offers(offers: list[Offer]) -> str:
    if not offers:
        return "There are no active offers right now."

    lines = ["Active offers:\n"]
    for offer in offers:
        lines.append(
            f"Offer #{offer.id}: {offer.description}\n"
            f"{offer.remaining_quantity} portions available"
        )
    return "\n\n".join(lines)


def create_offer(db: Session, description: str, quantity: int) -> Offer:
    offer = Offer(
        description=description,
        quantity=quantity,
        remaining_quantity=quantity,
        active=True,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    logger.info("Created offer #%s", offer.id)
    return offer


def parse_new_offer(argument: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"(.+?)\s*-\s*(\d+)(?:\s+.*)?", argument)
    if not match:
        return None

    description = match.group(1).strip()
    quantity = int(match.group(2))
    if not description or quantity <= 0:
        return None
    return description, quantity


def notify_students(db: Session, offer: Offer) -> None:
    students = list(db.scalars(select(Student).order_by(Student.id)))
    for student in students:
        safe_send_claim_button(student.phone_nr, offer)


def claim_offer(db: Session, phone: str, offer_id: int) -> str:
    student = db.scalar(select(Student).where(Student.phone_nr == phone))
    if student is None:
        return registration_help()

    offer = db.get(Offer, offer_id)
    if offer is None or not offer.active:
        return "Sorry, that offer is no longer available."

    existing_claim = db.scalar(
        select(Claim).where(Claim.offer_id == offer_id, Claim.student_id == student.id)
    )
    if existing_claim:
        return "You already claimed this offer."

    updated = db.execute(
        update(Offer)
        .where(
            Offer.id == offer_id,
            Offer.active.is_(True),
            Offer.remaining_quantity > 0,
        )
        .values(remaining_quantity=Offer.remaining_quantity - 1)
    )
    if updated.rowcount != 1:
        db.rollback()
        return "Sorry, this offer is sold out."

    db.add(Claim(offer_id=offer_id, student_id=student.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return "You already claimed this offer."

    db.refresh(offer)
    logger.info("Student ...%s claimed offer #%s", phone[-4:], offer_id)
    return (
        "Claimed!\n\n"
        f"You successfully claimed 1 portion of {offer.description}.\n"
        f"Remaining: {offer.remaining_quantity}"
    )


def handle_staff_command(db: Session, staff: Staff, command: str, argument: str) -> str:
    if command == "/new":
        parsed = parse_new_offer(argument)
        if parsed is None:
            return "Please use:\n\n/new Description - Quantity\n\nExample:\n/new Pizza - 10 slices"
        description, quantity = parsed
        offer = create_offer(db, description, quantity)
        notify_students(db, offer)
        return f"Offer #{offer.id} created and students were notified."

    if command == "/cancel":
        if not argument.isdigit():
            return "Please use:\n\n/cancel OfferID\n\nExample:\n/cancel 5"
        offer = db.get(Offer, int(argument))
        if offer is None or not offer.active:
            return "That offer does not exist or is already cancelled."
        offer.active = False
        db.commit()
        return f"Offer #{offer.id} cancelled."

    if command.startswith("/"):
        return "Sorry, I don't understand that command.\n\nTry:\n/new Food - Quantity\n/offers"

    return "Staff commands:\n/new Food - Quantity\n/offers\n/cancel OfferID"


def handle_text_command(db: Session, phone: str, body: str) -> str:
    words = body.split(maxsplit=1)
    command = words[0].lower() if words else ""
    argument = words[1].strip() if len(words) == 2 else ""

    student = db.scalar(select(Student).where(Student.phone_nr == phone))
    staff = db.scalar(select(Staff).where(Staff.phone_nr == phone))

    if command == "/register":
        if not argument:
            return "Please provide your name.\n\nExample:\n/register Bob Smith"
        return handle_register(db, phone, argument, as_staff=False)

    if command == "/staff":
        if not argument:
            return "Please provide your name.\n\nExample:\n/staff John Smith"
        return handle_register(db, phone, argument, as_staff=True)

    if not student and not staff:
        return registration_help()

    if command == "/offers":
        offers = list(
            db.scalars(
                select(Offer)
                .where(Offer.active.is_(True), Offer.remaining_quantity > 0)
                .order_by(Offer.id)
            )
        )
        return format_offers(offers)

    if staff:
        return handle_staff_command(db, staff, command, argument)

    if command.startswith("/"):
        return "Sorry, I don't understand that command.\n\nTry:\n/offers"

    return "Send /offers to see active leftover food offers."


def dashboard_html(db: Session) -> str:
    students = db.scalar(select(func.count()).select_from(Student)) or 0
    staff = db.scalar(select(func.count()).select_from(Staff)) or 0
    active_offers = list(
        db.scalars(select(Offer).where(Offer.active.is_(True)).order_by(Offer.id))
    )
    total_offered = db.scalar(select(func.coalesce(func.sum(Offer.quantity), 0))) or 0
    total_claimed = db.scalar(select(func.count()).select_from(Claim)) or 0

    offer_rows = "".join(
        "<tr>"
        f"<td>#{offer.id}</td>"
        f"<td>{escape(offer.description)}</td>"
        f"<td>{offer.quantity}</td>"
        f"<td>{offer.remaining_quantity}</td>"
        f"<td>{offer.quantity - offer.remaining_quantity}</td>"
        "</tr>"
        for offer in active_offers
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>PlateShare dashboard</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
.stats{{display:flex;gap:1rem;flex-wrap:wrap}}.stat{{border:1px solid #ccc;padding:1rem;min-width:120px}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}th,td{{border:1px solid #ccc;padding:.5rem;text-align:left}}</style>
</head><body><h1>PlateShare dashboard</h1><div class="stats">
<div class="stat">Students<br><strong>{students}</strong></div>
<div class="stat">Staff<br><strong>{staff}</strong></div>
<div class="stat">Portions offered<br><strong>{total_offered}</strong></div>
<div class="stat">Portions claimed<br><strong>{total_claimed}</strong></div>
<div class="stat">Food saved<br><strong>{total_claimed} portions</strong></div>
</div><h2>Active offers</h2><table><tr><th>Offer</th><th>Description</th>
<th>Quantity</th><th>Remaining</th><th>Claims</th></tr>{offer_rows}</table></body></html>"""


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)) -> str:
    return dashboard_html(db)


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> str:
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if mode == "subscribe" and expected_token and verify_token == expected_token:
        return challenge or ""
    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    payload = await request.json()
    details = get_message_details(payload)
    if details is None:
        return {"status": "ignored"}

    phone, body = details
    logger.info("Received WhatsApp message from ...%s", phone[-4:])
    if body.startswith("claim:"):
        offer_id_text = body.removeprefix("claim:")
        if not offer_id_text.isdigit():
            safe_send_text(phone, "Sorry, that claim button is invalid.")
            return {"status": "ok"}
        response = claim_offer(db, phone, int(offer_id_text))
        safe_send_text(phone, response)
        return {"status": "ok"}

    if not body:
        safe_send_text(phone, "Please send a text command, such as /offers.")
        return {"status": "ok"}

    response = handle_text_command(db, phone, body)
    safe_send_text(phone, response)
    return {"status": "ok"}