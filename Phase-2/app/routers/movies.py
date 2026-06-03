"""
Movies router. Read endpoints are public; create/update/delete require admin.
"""

from datetime import datetime, date as date_cls
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import APIError
from app.models import Movie, Showing, Hall, BookingSeat, Booking, Seat
from app.schemas import (
    MovieCreate,
    MovieUpdate,
    MoviePublic,
    MovieList,
    ShowingListItem,
    ShowingListResponse,
)
from app.security import require_admin

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("", response_model=MovieList)
async def list_movies(
    genre: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Movie).where(Movie.is_active == True)  # noqa: E712
    if genre:
        stmt = stmt.where(Movie.genre == genre)
    if search:
        stmt = stmt.where(Movie.title.ilike(f"%{search}%"))

    # Total count for pagination metadata.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(Movie.id)
    rows = (await db.execute(stmt)).scalars().all()
    return MovieList(items=[MoviePublic.model_validate(m) for m in rows], page=page, page_size=page_size, total=total)


@router.get("/{movie_id}", response_model=MoviePublic)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise APIError(404, "NOT_FOUND", "Movie not found.")
    return movie


@router.post("", response_model=MoviePublic, status_code=status.HTTP_201_CREATED)
async def create_movie(
    payload: MovieCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    movie = Movie(**payload.model_dump())
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    return movie


@router.patch("/{movie_id}", response_model=MoviePublic)
async def update_movie(
    movie_id: int,
    payload: MovieUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise APIError(404, "NOT_FOUND", "Movie not found.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(movie, k, v)
    await db.commit()
    await db.refresh(movie)
    return movie


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise APIError(404, "NOT_FOUND", "Movie not found.")

    # Admins can soft-delete any movie they like — even ones with upcoming
    # showings. The showings remain in the DB but the movie just gets flagged
    # inactive so it disappears from customer-facing listings.
    movie.is_active = False
    await db.commit()


@router.get("/{movie_id}/showings", response_model=ShowingListResponse)
async def list_movie_showings(
    movie_id: int,
    date: Optional[date_cls] = None,
    db: AsyncSession = Depends(get_db),
):
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise APIError(404, "NOT_FOUND", "Movie not found.")

    stmt = (
        select(Showing, Hall)
        .join(Hall, Hall.id == Showing.hall_id)
        .where(Showing.movie_id == movie_id)
        .order_by(Showing.start_time)
    )
    if date:
        # Match anything starting on that calendar date.
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        stmt = stmt.where(Showing.start_time >= start, Showing.start_time <= end)

    rows = (await db.execute(stmt)).all()

    items: list[ShowingListItem] = []
    for showing, hall in rows:
        # Compute occupancy + free-seat count for the list view.
        total_seats = (await db.execute(
            select(func.count()).select_from(Seat).where(Seat.hall_id == hall.id)
        )).scalar_one()
        booked = (await db.execute(
            select(func.count()).select_from(BookingSeat)
            .join(Booking, Booking.id == BookingSeat.booking_id)
            .where(BookingSeat.showing_id == showing.id, Booking.status == "confirmed")
        )).scalar_one()
        occ = (booked / total_seats) if total_seats else 0.0

        items.append(ShowingListItem(
            id=showing.id,
            movie_id=showing.movie_id,
            hall_id=showing.hall_id,
            hall_name=hall.name,
            start_time=showing.start_time,
            base_price=showing.base_price,
            occupancy_rate=round(occ, 2),
            seats_total=total_seats,
            seats_available=total_seats - booked,
            status=showing.status,
        ))
    return ShowingListResponse(items=items)
