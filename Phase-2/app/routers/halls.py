"""
Halls router (admin only).

POST /halls         create a hall (and optionally explicit seats; otherwise auto-generate)
GET  /halls         list halls with their seat layout
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.errors import APIError
from app.models import Hall, Seat
from app.schemas import HallCreate, HallPublic
from app.security import require_admin

router = APIRouter(prefix="/halls", tags=["halls"])


def _row_label(index: int) -> str:
    """0 -> A, 1 -> B, ... 25 -> Z, 26 -> AA, ..."""
    label = ""
    i = index
    while True:
        label = chr(ord("A") + (i % 26)) + label
        i = i // 26 - 1
        if i < 0:
            break
    return label


@router.post("", response_model=HallPublic, status_code=status.HTTP_201_CREATED)
async def create_hall(
    payload: HallCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    # Reject duplicate names early.
    existing = await db.execute(select(Hall).where(Hall.name == payload.name))
    if existing.scalar_one_or_none():
        raise APIError(409, "HALL_EXISTS", f"A hall named '{payload.name}' already exists.")

    hall = Hall(name=payload.name, rows_count=payload.rows_count, cols_count=payload.cols_count)
    db.add(hall)
    await db.flush()  # need hall.id before adding seats

    if payload.seats:
        for s in payload.seats:
            db.add(Seat(
                hall_id=hall.id,
                row_label=s.row_label,
                seat_number=s.seat_number,
                seat_type=s.seat_type,
            ))
    else:
        # Auto-generate rows_count x cols_count standard seats.
        for r in range(payload.rows_count):
            for c in range(payload.cols_count):
                db.add(Seat(
                    hall_id=hall.id,
                    row_label=_row_label(r),
                    seat_number=c + 1,
                    seat_type="standard",
                ))

    await db.commit()

    # Reload with seats relationship populated.
    result = await db.execute(
        select(Hall).options(selectinload(Hall.seats)).where(Hall.id == hall.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[HallPublic])
async def list_halls(db: AsyncSession = Depends(get_db), _admin=Depends(require_admin)):
    result = await db.execute(select(Hall).options(selectinload(Hall.seats)).order_by(Hall.id))
    return result.scalars().all()
