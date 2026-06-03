"""
Payments router.

GET  /payments/config          Return Stripe publishable key to the frontend
POST /payments/webhook         Stripe webhook — confirms or cancels bookings
"""

import logging
from datetime import datetime

import stripe
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
from app.database import get_db
from app.errors import APIError
from app.models import Booking, BookingSeat
from app.services.holds import release_holds

stripe.api_key = STRIPE_SECRET_KEY
log = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/config")
async def get_stripe_config():
    """Return the Stripe publishable key so the frontend can initialise Stripe.js."""
    if not STRIPE_PUBLISHABLE_KEY:
        raise APIError(501, "PAYMENT_NOT_CONFIGURED",
                       "Payment processing is not configured on this server.")
    return {"publishable_key": STRIPE_PUBLISHABLE_KEY}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Stripe calls this endpoint after every payment event.
    We handle:
      - payment_intent.succeeded   → confirm the booking
      - payment_intent.payment_failed → cancel booking, free seats
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify the event came from Stripe (skip in dev if no secret is set).
    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.errors.SignatureVerificationError:
            log.warning("Stripe webhook: invalid signature")
            return JSONResponse(status_code=400, content={"error": "invalid signature"})
    else:
        import json
        event = json.loads(payload)

    intent = event.get("data", {}).get("object", {})
    intent_id = intent.get("id")
    event_type = event.get("type")

    log.info("Stripe webhook: %s  intent=%s", event_type, intent_id)

    if event_type == "payment_intent.succeeded":
        await _confirm_booking(intent_id, db)

    elif event_type in ("payment_intent.payment_failed", "payment_intent.canceled"):
        await _cancel_booking(intent_id, db)

    return {"received": True}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _confirm_booking(intent_id: str, db: AsyncSession) -> None:
    """Mark the booking confirmed once Stripe confirms payment."""
    booking = await _get_by_intent(intent_id, db)
    if not booking or booking.status != "pending_payment":
        return

    booking.status = "confirmed"
    booking.payment_expires_at = None
    await db.commit()
    log.info("Booking %d confirmed (intent %s)", booking.id, intent_id)


async def _cancel_booking(intent_id: str, db: AsyncSession) -> None:
    """Cancel the booking and free the seats when payment fails."""
    booking = await _get_by_intent(intent_id, db)
    if not booking or booking.status == "cancelled":
        return

    # Free the seat rows so they become available again.
    seat_ids = [bs.seat_id for bs in booking.seats]
    for bs in list(booking.seats):
        await db.delete(bs)

    booking.status = "cancelled"
    booking.cancelled_at = datetime.utcnow()
    await db.commit()

    # Also release any Redis holds still lingering.
    try:
        await release_holds(booking.showing_id, seat_ids, booking.user_id)
    except Exception:
        pass

    log.info("Booking %d cancelled (intent %s)", booking.id, intent_id)


async def _get_by_intent(intent_id: str, db: AsyncSession):
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Booking)
        .options(selectinload(Booking.seats))
        .where(Booking.payment_intent_id == intent_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()
