"""
Pydantic schemas for the Movie Reservation API (Phase 3 - Security).

Phase-3 hardening over Phase-2:
  - Strict mode + extra="forbid" on every inbound request body
  - Length / regex / numeric bounds on every free field
  - Enums for fixed-vocabulary fields (role, seat_type, status, rating, tier)
  - Strong password policy (length + upper + lower + digit)
  - Future-dated start_time on showings
  - Non-empty, de-duplicated, size-capped seat_ids on holds & bookings
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    field_validator,
)


# ---------- Enums ----------

class UserRole(str, Enum):
    customer = "customer"
    admin = "admin"


class SeatType(str, Enum):
    standard = "standard"
    vip = "vip"


class SeatStatus(str, Enum):
    available = "available"
    held = "held"
    booked = "booked"


class ShowingStatus(str, Enum):
    scheduled = "scheduled"
    cancelled = "cancelled"
    completed = "completed"


class BookingStatus(str, Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"


class PricingTier(str, Enum):
    low = "low"
    mid = "mid"
    high = "high"


class MovieRating(str, Enum):
    G = "G"
    PG = "PG"
    PG13 = "PG-13"
    R = "R"
    NC17 = "NC-17"


# ---------- Base ----------

class StrictModel(BaseModel):
    """Inbound bodies: no unknown fields, trim whitespace."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


MAX_SEATS_PER_REQUEST = 10  # anti-DoS cap


# ---------- Auth ----------

class RegisterRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: Optional[datetime] = None


# ---------- Movies ----------

class MovieBase(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    duration_minutes: int = Field(gt=0, le=600)
    genre: Optional[str] = Field(default=None, max_length=50)
    rating: Optional[MovieRating] = None
    poster_url: Optional[str] = Field(default=None, max_length=500, pattern=r"^https?://.+")


class MovieCreate(MovieBase):
    pass


class MovieUpdate(StrictModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=600)
    genre: Optional[str] = Field(default=None, max_length=50)
    rating: Optional[MovieRating] = None
    poster_url: Optional[str] = Field(default=None, max_length=500, pattern=r"^https?://.+")
    is_active: Optional[bool] = None


class MoviePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: Optional[str] = None
    duration_minutes: int
    genre: Optional[str] = None
    rating: Optional[str] = None
    poster_url: Optional[str] = None
    is_active: bool


class MovieList(BaseModel):
    items: list[MoviePublic]
    page: int
    page_size: int
    total: int


# ---------- Halls ----------

class SeatCreate(StrictModel):
    row_label: str = Field(min_length=1, max_length=3, pattern=r"^[A-Z]{1,3}$")
    seat_number: int = Field(gt=0, le=999)
    seat_type: SeatType = SeatType.standard


class HallCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    rows_count: int = Field(gt=0, le=50)
    cols_count: int = Field(gt=0, le=50)
    seats: Optional[list[SeatCreate]] = Field(default=None, max_length=2500)


class SeatPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    row_label: str
    seat_number: int
    seat_type: SeatType


class HallPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    rows_count: int
    cols_count: int
    seats: list[SeatPublic] = []


# ---------- Showings ----------

class ShowingCreate(StrictModel):
    movie_id: int = Field(gt=0)
    hall_id: int = Field(gt=0)
    start_time: datetime
    base_price: Decimal = Field(gt=Decimal("0"), le=Decimal("9999.99"))

    @field_validator("start_time")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc) if v.tzinfo else datetime.utcnow()
        if v <= now:
            raise ValueError("start_time must be in the future.")
        return v

    @field_validator("base_price")
    @classmethod
    def two_decimals(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("base_price must have at most 2 decimal places.")
        return v


class ShowingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    movie_id: int
    hall_id: int
    start_time: datetime
    base_price: Decimal
    status: ShowingStatus


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
    status: ShowingStatus


class ShowingListResponse(BaseModel):
    items: list[ShowingListItem]


# ---------- Seat map ----------

class SeatMapSeat(BaseModel):
    id: int
    row_label: str
    seat_number: int
    seat_type: SeatType
    status: SeatStatus
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
    pricing_tier: PricingTier
    tier_multiplier: float
    hall: SeatMapHall
    seats: list[SeatMapSeat]


# ---------- Holds / Bookings helpers ----------

def _validate_seat_ids(v: list[int]) -> list[int]:
    if not v:
        raise ValueError("seat_ids must contain at least one seat.")
    if len(v) > MAX_SEATS_PER_REQUEST:
        raise ValueError(f"Cannot request more than {MAX_SEATS_PER_REQUEST} seats at once.")
    if any(sid <= 0 for sid in v):
        raise ValueError("seat_ids must be positive integers.")
    if len(set(v)) != len(v):
        raise ValueError("seat_ids contains duplicates.")
    return v


class HoldRequest(StrictModel):
    seat_ids: list[int]

    @field_validator("seat_ids")
    @classmethod
    def _v(cls, v):
        return _validate_seat_ids(v)


class HoldResponse(BaseModel):
    showing_id: int
    held_seat_ids: list[int]
    expires_at: datetime
    ttl_seconds: int


class HoldReleaseRequest(StrictModel):
    seat_ids: Optional[list[int]] = None

    @field_validator("seat_ids")
    @classmethod
    def _v(cls, v):
        if v is None:
            return v
        return _validate_seat_ids(v)


# ---------- Bookings ----------

class BookingCreate(StrictModel):
    showing_id: int = Field(gt=0)
    seat_ids: list[int]

    @field_validator("seat_ids")
    @classmethod
    def _v(cls, v):
        return _validate_seat_ids(v)


class BookingSeatPublic(BaseModel):
    seat_id: int
    row_label: str
    seat_number: int
    price_at_booking: Decimal


class BookingPublic(BaseModel):
    id: int
    showing_id: int
    user_id: int
    status: BookingStatus
    ticket_code: str
    total_price: Decimal
    created_at: datetime
    seats: list[BookingSeatPublic]


class BookingListItem(BaseModel):
    id: int
    showing_id: int
    movie_title: str
    hall_name: str
    start_time: datetime
    status: BookingStatus
    total_price: Decimal
    ticket_code: str
    created_at: datetime


class BookingList(BaseModel):
    items: list[BookingListItem]


class BookingCancelResponse(BaseModel):
    id: int
    status: BookingStatus
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
    seat_type: SeatType


class TicketResponse(BaseModel):
    ticket_code: str
    qr_payload: str
    movie: TicketMovie
    showing: TicketShowing
    seats: list[TicketSeat]
    total_price: Decimal
    issued_at: datetime
