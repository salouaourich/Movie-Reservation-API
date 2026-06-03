"""
Showings router.

POST /showings                     admin: create a new showing
GET  /showings/{id}                public: showing detail
GET  /showings/{id}/seats          public: seat map with live dynamic prices
POST /showings/{id}/holds          customer: acquire seat holds (atomic)
DELETE /showings/{id}/holds        customer: release seat holds
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.errors import APIError
from app.models import Showing, Hall, Seat, Booking, BookingSeat, Movie
from app.schemas import (
    ShowingCreate,
    ShowingPublic,
    SeatMapResponse,
    SeatMapHall,
    SeatMapSeat,
    HoldRequest,
    HoldResponse,
    HoldReleaseRequest,
)
from app.security import require_admin, require_customer
from app.services.pricing import calculate_seat_price, pricing_tier
from app.services.holds import (
    acquire_holds,
    release_holds,
    release_all_user_holds,
    get_all_held_seats_for_showing,
)

router = APIRouter(prefix="/showings", tags=["showings"])


async def _occupancy(db: AsyncSession, showing: Showing) -> tuple[int, int, float]:
    """Return (booked_count, total_seats, occupancy_rate) for a showing."""
    total = (await db.execute(
        select(func.count()).select_from(Seat).where(Seat.hall_id == showing.hall_id)
    )).scalar_one()
    booked = (await db.execute(
        select(func.count()).select_from(BookingSeat)
        .join(Booking, Booking.id == BookingSeat.booking_id)
        .where(BookingSeat.showing_id == showing.id, Booking.status == "confirmed")
    )).scalar_one()
    rate = (booked / total) if total else 0.0
    return booked, total, rate


@router.post("", response_model=ShowingPublic, status_code=status.HTTP_201_CREATED)
async def create_showing(
    payload: ShowingCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    # Validate movie + hall exist.
    movie = await db.get(Movie, payload.movie_id)
    if not movie:
        raise APIError(404, "NOT_FOUND", "Movie not found.")
    hall = await db.get(Hall, payload.hall_id)
    if not hall:
        raise APIError(404, "NOT_FOUND", "Hall not found.")

    # No two showings can overlap in the same hall. We approximate "overlap"
    # by checking start_time within ± movie.duration_minutes of another showing's start.
    window = timedelta(minutes=movie.duration_minutes)
    clash_stmt = select(Showing).where(
        and_(
            Showing.hall_id == payload.hall_id,
            Showing.start_time > payload.start_time - window,
            Showing.start_time < payload.start_time + window,
        )
    )
    if (await db.execute(clash_stmt)).scalar_one_or_none():
        raise APIError(409, "TIME_OVERLAP", "Another showing overlaps this time slot in this hall.")

    showing = Showing(**payload.model_dump())
    db.add(showing)
    await db.commit()
    await db.refresh(showing)
    return showing


@router.get("/{showing_id}", response_model=ShowingPublic)
async def get_showing(showing_id: int, db: AsyncSession = Depends(get_db)):
    showing = await db.get(Showing, showing_id)
    if not showing:
        raise APIError(404, "NOT_FOUND", "Showing not found.")
    return showing


@router.get("/{showing_id}/seats", response_model=SeatMapResponse)
async def get_seat_map(showing_id: int, db: AsyncSession = Depends(get_db)):
    """
    The dynamic pricing endpoint.
    For each seat in the hall, returns: status (available/held/booked)
    AND the live price (base_price * tier_multiplier * vip_multiplier).
    """
    showing = await db.get(Showing, showing_id)
    if not showing:
        raise APIError(404, "NOT_FOUND", "Showing not found.")
    hall = await db.get(Hall, showing.hall_id)

    # 1. compute occupancy + tier from DB state.
    _, _, occ_rate = await _occupancy(db, showing)
    tier, multiplier = pricing_tier(occ_rate)

    # 2. fetch all seats in this hall.
    seats = (await db.execute(
        select(Seat).where(Seat.hall_id == hall.id).order_by(Seat.row_label, Seat.seat_number)
    )).scalars().all()

    # 3. find which seats are booked (DB) and which are currently held (Redis).
    booked_rows = (await db.execute(
        select(BookingSeat.seat_id)
        .join(Booking, Booking.id == BookingSeat.booking_id)
        .where(BookingSeat.showing_id == showing.id, Booking.status == "confirmed")
    )).scalars().all()
    booked_ids = set(booked_rows)
    held_ids = await get_all_held_seats_for_showing(showing.id)

    # 4. build response — calculate price per seat.
    out_seats: list[SeatMapSeat] = []
    for s in seats:
        if s.id in booked_ids:
            status_str = "booked"
        elif s.id in held_ids:
            status_str = "held"
        else:
            status_str = "available"
        price = calculate_seat_price(showing.base_price, occ_rate, s.seat_type)
        out_seats.append(SeatMapSeat(
            id=s.id, row_label=s.row_label, seat_number=s.seat_number,
            seat_type=s.seat_type, status=status_str, price=price,
        ))

    return SeatMapResponse(
        showing_id=showing.id,
        base_price=showing.base_price,
        occupancy_rate=round(occ_rate, 2),
        pricing_tier=tier,
        tier_multiplier=float(multiplier),
        hall=SeatMapHall(id=hall.id, name=hall.name, rows_count=hall.rows_count, cols_count=hall.cols_count),
        seats=out_seats,
    )


@router.post("/{showing_id}/holds", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
async def create_holds(
    showing_id: int,
    payload: HoldRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_customer),
):
    if not payload.seat_ids:
        raise APIError(400, "EMPTY_LIST", "seat_ids must not be empty.")

    showing = await db.get(Showing, showing_id)
    if not showing:
        raise APIError(404, "NOT_FOUND", "Showing not found.")

    # Reject seats that don't belong to this showing's hall.
    valid_seat_ids = set((await db.execute(
        select(Seat.id).where(Seat.hall_id == showing.hall_id, Seat.id.in_(payload.seat_ids))
    )).scalars().all())
    invalid = [sid for sid in payload.seat_ids if sid not in valid_seat_ids]
    if invalid:
        raise APIError(400, "INVALID_SEATS", "Some seats don't belong to this showing.", {"seat_ids": invalid})

    # Reject seats that are already booked (DB).
    already_booked = (await db.execute(
        select(BookingSeat.seat_id)
        .join(Booking, Booking.id == BookingSeat.booking_id)
        .where(
            BookingSeat.showing_id == showing.id,
            Booking.status == "confirmed",
            BookingSeat.seat_id.in_(payload.seat_ids),
        )
    )).scalars().all()
    if already_booked:
        raise APIError(409, "SEAT_UNAVAILABLE",
                       f"Seats {list(already_booked)} are already booked.",
                       {"seat_ids": list(already_booked)})

    # Try to atomically acquire all holds.
    ok, conflicts, expires_at = await acquire_holds(showing.id, payload.seat_ids, user.id)
    if not ok:
        raise APIError(409, "SEAT_UNAVAILABLE",
                       f"Seats {conflicts} are already held by another user.",
                       {"seat_ids": conflicts})

    from app.config import HOLD_TTL_SECONDS
    return HoldResponse(
        showing_id=showing.id,
        held_seat_ids=payload.seat_ids,
        expires_at=expires_at,
        ttl_seconds=HOLD_TTL_SECONDS,
    )


@router.delete("/{showing_id}/holds", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holds(
    showing_id: int,
    payload: HoldReleaseRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_customer),
):
    showing = await db.get(Showing, showing_id)
    if not showing:
        raise APIError(404, "NOT_FOUND", "Showing not found.")

    if payload.seat_ids:
        await release_holds(showing.id, payload.seat_ids, user.id)
    else:
        await release_all_user_holds(showing.id, user.id)
