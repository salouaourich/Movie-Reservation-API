"""
SQLAlchemy ORM models. These mirror the ERD from Phase 1 exactly:
  users, movies, halls, seats, showings, bookings, booking_seats.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="customer", nullable=False)  # customer | admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    genre: Mapped[str | None] = mapped_column(String(50), index=True)
    rating: Mapped[str | None] = mapped_column(String(10))
    # Text (not String(500)) so admins can paste a long URL *or* upload a
    # base64-encoded image (data:image/...;base64,...) which routinely runs
    # well over 100 KB of characters for a real poster.
    poster_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    showings: Mapped[list["Showing"]] = relationship(back_populates="movie")


class Hall(Base):
    __tablename__ = "halls"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    rows_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cols_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    seats: Mapped[list["Seat"]] = relationship(back_populates="hall", cascade="all, delete-orphan")
    showings: Mapped[list["Showing"]] = relationship(back_populates="hall")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("hall_id", "row_label", "seat_number", name="uq_seat_in_hall"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.id", ondelete="CASCADE"), nullable=False, index=True)
    row_label: Mapped[str] = mapped_column(String(5), nullable=False)
    seat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_type: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)  # standard | vip

    hall: Mapped["Hall"] = relationship(back_populates="seats")


class Showing(Base):
    __tablename__ = "showings"

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False, index=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.id"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    movie: Mapped["Movie"] = relationship(back_populates="showings")
    hall: Mapped["Hall"] = relationship(back_populates="showings")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="showing")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    showing_id: Mapped[int] = mapped_column(ForeignKey("showings.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)  # confirmed | cancelled
    ticket_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="bookings")
    showing: Mapped["Showing"] = relationship(back_populates="bookings")
    seats: Mapped[list["BookingSeat"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )


class BookingSeat(Base):
    """
    Join table linking a booking to specific seats. The unique constraint on
    (showing_id, seat_id) is what enforces "no double booking" at the DB level —
    even if two transactions race past Redis, the DB will reject the second insert.
    """

    __tablename__ = "booking_seats"
    __table_args__ = (
        UniqueConstraint("showing_id", "seat_id", name="uq_seat_per_showing"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    showing_id: Mapped[int] = mapped_column(ForeignKey("showings.id"), nullable=False, index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), nullable=False)
    price_at_booking: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    booking: Mapped["Booking"] = relationship(back_populates="seats")
    seat: Mapped["Seat"] = relationship()
