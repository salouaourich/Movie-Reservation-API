"""
Bookings router (customer-facing).

POST /bookings                     confirm holds into a paid booking
GET  /bookings/me                  current user's booking history
GET  /bookings/{id}                booking detail (owner or admin)
DELETE /bookings/{id}              cancel a booking (frees seats)
GET  /bookings/{id}/ticket         e-ticket details
"""

import secrets
from datetime import datetime, timedelta
from decimal import Decimal

import stripe
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.config import STRIPE_SECRET_KEY, PAYMENT_EXPIRE_MINUTES
from app.database import get_db
from app.errors import APIError
from app.models import Booking, BookingSeat, Seat, Showing, Hall, Movie
from app.schemas import (
    BookingCreate,
    BookingPublic,
    BookingPendingResponse,
    BookingSeatPublic,
    BookingList,
    BookingListItem,
    BookingCancelResponse,
    TicketResponse,
    TicketMovie,
    TicketShowing,
    TicketSeat,
)
from app.security import get_current_user, require_customer
from app.services.pricing import calculate_seat_price, pricing_tier
from app.services.holds import user_owns_holds, release_holds

stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _generate_ticket_code() -> str:
    """Produce a short, URL-safe ticket code, e.g. TKT-7G2K-9XW1."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no confusing chars
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"TKT-{part1}-{part2}"


@router.post("", response_model=BookingPendingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_customer),
):
    """
    Creates a booking in 'pending_payment' state and returns a Stripe
    PaymentIntent client_secret. The frontend must complete payment using
    Stripe.js; the webhook at POST /payments/webhook then confirms the booking.
    Unpaid bookings are automatically cancelled after PAYMENT_EXPIRE_MINUTES.
    """
    if not payload.seat_ids:
        raise APIError(400, "EMPTY_LIST", "seat_ids must not be empty.")

    showing = await db.get(Showing, payload.showing_id)
    if not showing:
        raise APIError(404, "NOT_FOUND", "Showing not found.")

    # Caller must currently own a hold on every seat.
    ok, missing = await user_owns_holds(showing.id, payload.seat_ids, user.id)
    if not ok:
        raise APIError(409, "HOLD_REQUIRED",
                       f"You do not hold seats {missing} (or the hold expired).",
                       {"seat_ids": missing})

    # Clean up any stale pending_payment bookings the SAME user has for this
    # showing. Without this, a user who clicks "Proceed to payment" twice
    # would hit the unique-seat constraint on their own previous attempt.
    stale_stmt = (
        select(Booking)
        .options(selectinload(Booking.seats))
        .where(
            Booking.user_id == user.id,
            Booking.showing_id == showing.id,
            Booking.status == "pending_payment",
        )
    )
    stale = (await db.execute(stale_stmt)).scalars().all()
    for old in stale:
        # Cancel the old Stripe PaymentIntent so it doesn't keep charging.
        if old.payment_intent_id:
            try:
                stripe.PaymentIntent.cancel(old.payment_intent_id)
            except Exception:
                pass
        for bs in list(old.seats):
            await db.delete(bs)
        old.status = "cancelled"
        old.cancelled_at = datetime.utcnow()
    if stale:
        await db.flush()

    # Compute final prices using the CURRENT occupancy.
    total_seats = (await db.execute(
        select(func.count()).select_from(Seat).where(Seat.hall_id == showing.hall_id)
    )).scalar_one()
    booked = (await db.execute(
        select(func.count()).select_from(BookingSeat)
        .join(Booking, Booking.id == BookingSeat.booking_id)
        .where(BookingSeat.showing_id == showing.id, Booking.status == "confirmed")
    )).scalar_one()
    occ_rate = (booked / total_seats) if total_seats else 0.0

    # Fetch seat rows for type + label info.
    seats = (await db.execute(select(Seat).where(Seat.id.in_(payload.seat_ids)))).scalars().all()
    seat_by_id = {s.id: s for s in seats}

    # Calculate total price first (needed for Stripe PaymentIntent).
    total = Decimal("0.00")
    seat_prices: dict[int, Decimal] = {}
    for sid in payload.seat_ids:
        seat = seat_by_id.get(sid)
        if not seat:
            raise APIError(400, "INVALID_SEATS", f"Seat {sid} not found.")
        price = calculate_seat_price(showing.base_price, occ_rate, seat.seat_type)
        seat_prices[sid] = price
        total += price

    # Create Stripe PaymentIntent (amount in cents).
    if not STRIPE_SECRET_KEY:
        raise APIError(501, "PAYMENT_NOT_CONFIGURED",
                       "Payment processing is not configured on this server.")
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(total * 100),   # USD cents
            currency="usd",
            metadata={
                "user_id":    str(user.id),
                "showing_id": str(showing.id),
            },
        )
    except stripe.StripeError as e:
        raise APIError(502, "STRIPE_ERROR", f"Payment setup failed: {e.user_message or str(e)}")

    # Persist the booking (pending_payment) and seat rows.
    expires_at = datetime.utcnow() + timedelta(minutes=PAYMENT_EXPIRE_MINUTES)
    booking = Booking(
        user_id=user.id,
        showing_id=showing.id,
        status="pending_payment",
        ticket_code=_generate_ticket_code(),
        total_price=total,
        payment_intent_id=intent.id,
        payment_expires_at=expires_at,
    )
    db.add(booking)
    await db.flush()  # need booking.id

    booking_seats_out: list[BookingSeatPublic] = []
    for sid in payload.seat_ids:
        seat = seat_by_id[sid]
        price = seat_prices[sid]
        db.add(BookingSeat(
            booking_id=booking.id,
            showing_id=showing.id,
            seat_id=sid,
            price_at_booking=price,
        ))
        booking_seats_out.append(BookingSeatPublic(
            seat_id=sid,
            row_label=seat.row_label,
            seat_number=seat.seat_number,
            price_at_booking=price,
        ))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Cancel the orphaned PaymentIntent so Stripe doesn't keep it open.
        try:
            stripe.PaymentIntent.cancel(intent.id)
        except Exception:
            pass
        raise APIError(409, "SEAT_UNAVAILABLE", "One or more seats were just booked by another user.")

    await db.refresh(booking)
    return BookingPendingResponse(
        id=booking.id,
        showing_id=booking.showing_id,
        user_id=booking.user_id,
        status=booking.status,
        ticket_code=booking.ticket_code,
        total_price=booking.total_price,
        created_at=booking.created_at,
        payment_expires_at=booking.payment_expires_at,
        client_secret=intent.client_secret,
        seats=booking_seats_out,
    )


@router.get("/me", response_model=BookingList)
async def my_bookings(db: AsyncSession = Depends(get_db), user=Depends(require_customer)):
    stmt = (
        select(Booking, Showing, Movie, Hall)
        .join(Showing, Showing.id == Booking.showing_id)
        .join(Movie, Movie.id == Showing.movie_id)
        .join(Hall, Hall.id == Showing.hall_id)
        .where(Booking.user_id == user.id)
        .order_by(Booking.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return BookingList(items=[
        BookingListItem(
            id=b.id,
            showing_id=b.showing_id,
            movie_title=m.title,
            hall_name=h.name,
            start_time=s.start_time,
            status=b.status,
            total_price=b.total_price,
            ticket_code=b.ticket_code,
            created_at=b.created_at,
        )
        for b, s, m, h in rows
    ])


async def _load_booking_or_403(booking_id: int, user, db: AsyncSession) -> Booking:
    """Fetch a booking — caller must be owner or admin."""
    stmt = select(Booking).options(selectinload(Booking.seats)).where(Booking.id == booking_id)
    booking = (await db.execute(stmt)).scalar_one_or_none()
    if not booking:
        raise APIError(404, "NOT_FOUND", "Booking not found.")
    if booking.user_id != user.id and user.role != "admin":
        raise APIError(403, "FORBIDDEN", "You don't have access to this booking.")
    return booking


@router.get("/{booking_id}", response_model=BookingPublic)
async def get_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    booking = await _load_booking_or_403(booking_id, user, db)
    # Build seat detail.
    seat_ids = [bs.seat_id for bs in booking.seats]
    seats = (await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))).scalars().all()
    seat_by_id = {s.id: s for s in seats}
    seats_out = [
        BookingSeatPublic(
            seat_id=bs.seat_id,
            row_label=seat_by_id[bs.seat_id].row_label,
            seat_number=seat_by_id[bs.seat_id].seat_number,
            price_at_booking=bs.price_at_booking,
        )
        for bs in booking.seats
    ]
    return BookingPublic(
        id=booking.id,
        showing_id=booking.showing_id,
        user_id=booking.user_id,
        status=booking.status,
        ticket_code=booking.ticket_code,
        total_price=booking.total_price,
        created_at=booking.created_at,
        seats=seats_out,
    )


@router.delete("/{booking_id}", response_model=BookingCancelResponse)
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    booking = await _load_booking_or_403(booking_id, user, db)
    if booking.status == "cancelled":
        # Idempotent — return current state.
        return BookingCancelResponse(id=booking.id, status="cancelled", cancelled_at=booking.cancelled_at or datetime.utcnow())

    # Refuse to cancel a showing that has already started.
    showing = await db.get(Showing, booking.showing_id)
    if showing and showing.start_time <= datetime.utcnow():
        raise APIError(409, "SHOWING_STARTED", "Cannot cancel — the showing has already started.")

    booking.status = "cancelled"
    booking.cancelled_at = datetime.utcnow()
    # Free the seats: delete booking_seats so the unique constraint releases them
    # and they become available again on the seat map.
    for bs in booking.seats:
        await db.delete(bs)
    await db.commit()
    return BookingCancelResponse(id=booking.id, status="cancelled", cancelled_at=booking.cancelled_at)


@router.get("/{booking_id}/ticket", response_model=TicketResponse)
async def get_ticket(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    booking = await _load_booking_or_403(booking_id, user, db)
    if booking.status == "cancelled":
        raise APIError(409, "BOOKING_CANCELLED", "This booking has been cancelled.")

    showing = await db.get(Showing, booking.showing_id)
    movie = await db.get(Movie, showing.movie_id)
    hall = await db.get(Hall, showing.hall_id)

    seat_ids = [bs.seat_id for bs in booking.seats]
    seats = (await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))).scalars().all()

    return TicketResponse(
        ticket_code=booking.ticket_code,
        qr_payload=booking.ticket_code,
        movie=TicketMovie(title=movie.title, duration_minutes=movie.duration_minutes, rating=movie.rating),
        showing=TicketShowing(start_time=showing.start_time, hall_name=hall.name),
        seats=[TicketSeat(row_label=s.row_label, seat_number=s.seat_number, seat_type=s.seat_type) for s in seats],
        total_price=booking.total_price,
        issued_at=booking.created_at,
    )
