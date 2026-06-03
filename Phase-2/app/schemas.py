"""
Pydantic schemas that match the Phase-1 API contract exactly.
Request shapes, response shapes, and error shapes all live here.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: Optional[datetime] = None


# ---------- Movies ----------

class MovieBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(gt=0)
    genre: Optional[str] = None
    rating: Optional[str] = None
    poster_url: Optional[str] = None


class MovieCreate(MovieBase):
    pass


class MovieUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    genre: Optional[str] = None
    rating: Optional[str] = None
    poster_url: Optional[str] = None
    is_active: Optional[bool] = None


class MoviePublic(MovieBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class MovieList(BaseModel):
    items: list[MoviePublic]
    page: int
    page_size: int
    total: int


# ---------- Halls ----------

class SeatCreate(BaseModel):
    row_label: str
    seat_number: int
    seat_type: str = "standard"


class HallCreate(BaseModel):
    name: str
    rows_count: int = Field(gt=0)
    cols_count: int = Field(gt=0)
    seats: Optional[list[SeatCreate]] = None


class SeatPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    row_label: str
    seat_number: int
    seat_type: str


class HallPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    rows_count: int
    cols_count: int
    seats: list[SeatPublic] = []


# ---------- Showings ----------

class ShowingCreate(BaseModel):
    movie_id: int
    hall_id: int
    start_time: datetime
    base_price: Decimal


class ShowingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    movie_id: int
    hall_id: int
    start_time: datetime
    base_price: Decimal
    status: str


class ShowingListItem(BaseModel):
    id: int
    movie_id: int
    hall_id: int
    hall_name: str
    start_time: datetime
    base_price: Decimal
    occupancy_rate: float
    seats_total: int
    seats_available: int
    status: str


class ShowingListResponse(BaseModel):
    items: list[ShowingListItem]


# ---------- Seat map (the dynamic pricing endpoint) ----------

class SeatMapSeat(BaseModel):
    id: int
    row_label: str
    seat_number: int
    seat_type: str
    status: str  # available | held | booked
    price: Decimal


class SeatMapHall(BaseModel):
    id: int
    name: str
    rows_count: int
    cols_count: int


class SeatMapResponse(BaseModel):
    showing_id: int
    base_price: Decimal
    occupancy_rate: float
    pricing_tier: str   # low | mid | high
    tier_multiplier: float
    hall: SeatMapHall
    seats: list[SeatMapSeat]


# ---------- Holds ----------

class HoldRequest(BaseModel):
    seat_ids: list[int]


class HoldResponse(BaseModel):
    showing_id: int
    held_seat_ids: list[int]
    expires_at: datetime
    ttl_seconds: int


class HoldReleaseRequest(BaseModel):
    seat_ids: Optional[list[int]] = None


# ---------- Bookings ----------

class BookingCreate(BaseModel):
    showing_id: int
    seat_ids: list[int]


class BookingSeatPublic(BaseModel):
    seat_id: int
    row_label: str
    seat_number: int
    price_at_booking: Decimal


class BookingPublic(BaseModel):
    id: int
    showing_id: int
    user_id: int
    status: str
    ticket_code: str
    total_price: Decimal
    created_at: datetime
    seats: list[BookingSeatPublic]


class BookingPendingResponse(BaseModel):
    """Returned immediately after POST /bookings — payment still required."""
    id: int
    showing_id: int
    user_id: int
    status: str          # always "pending_payment"
    ticket_code: str
    total_price: Decimal
    created_at: datetime
    payment_expires_at: datetime
    client_secret: str   # Stripe PaymentIntent client secret — pass to Stripe.js
    seats: list[BookingSeatPublic]


class BookingListItem(BaseModel):
    id: int
    showing_id: int
    movie_title: str
    hall_name: str
    start_time: datetime
    status: str
    total_price: Decimal
    ticket_code: str
    created_at: datetime


class BookingList(BaseModel):
    items: list[BookingListItem]


class BookingCancelResponse(BaseModel):
    id: int
    status: str
    cancelled_at: datetime


# ---------- Ticket ----------

class TicketMovie(BaseModel):
    title: str
    duration_minutes: int
    rating: Optional[str] = None


class TicketShowing(BaseModel):
    start_time: datetime
    hall_name: str


class TicketSeat(BaseModel):
    row_label: str
    seat_number: int
    seat_type: str


class TicketResponse(BaseModel):
    ticket_code: str
    qr_payload: str
    movie: TicketMovie
    showing: TicketShowing
    seats: list[TicketSeat]
    total_price: Decimal
    issued_at: datetime
