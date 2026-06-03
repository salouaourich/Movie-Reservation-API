"""
FastAPI entrypoint.

- Mounts every router under /api/v1
- Installs a global exception handler that re-shapes errors to:
    { "error": { "code": ..., "message": ..., "details": ... } }
- Enables CORS so the React dev server on :5173 can call this API
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import API_PREFIX
from app.database import AsyncSessionLocal, engine
from app.models import Booking, BookingSeat
from app.routers import auth, movies, halls, showings, bookings
from app.routers import payments

log = logging.getLogger(__name__)


# ── One-time schema migration: add payment columns if missing ────────────────

async def _ensure_payment_columns() -> None:
    """
    Idempotent: adds payment_intent_id and payment_expires_at columns to the
    bookings table if they don't already exist. Lets us add Stripe support
    without forcing a manual DB migration.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS "
                "payment_intent_id VARCHAR(100)"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_bookings_payment_intent_id "
                "ON bookings (payment_intent_id)"
            ))
            await conn.execute(text(
                "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS "
                "payment_expires_at TIMESTAMP"
            ))
        log.info("Payment columns ensured on bookings table.")
    except Exception:
        log.exception("Failed to ensure payment columns")


# ── Background task: expire unpaid bookings every 60 s ───────────────────────

async def _expire_pending_bookings() -> None:
    """Cancel bookings still in pending_payment past their deadline."""
    try:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Booking)
                .options(selectinload(Booking.seats))
                .where(
                    Booking.status == "pending_payment",
                    Booking.payment_expires_at <= datetime.utcnow(),
                )
            )
            expired = (await db.execute(stmt)).scalars().all()
            for booking in expired:
                for bs in list(booking.seats):
                    await db.delete(bs)
                booking.status = "cancelled"
                booking.cancelled_at = datetime.utcnow()
                log.info("Expired pending booking %d (payment timeout)", booking.id)
            if expired:
                await db.commit()
    except Exception:
        log.exception("Error in _expire_pending_bookings")


async def _cleanup_loop() -> None:
    """Infinite loop — runs cleanup every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        await _expire_pending_bookings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _ensure_payment_columns()
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Movie Reservation API",
    version="0.2.0",
    description="Phase 2 — Cinema seat booking with dynamic pricing.",
    lifespan=lifespan,
)

# Allow the React frontend to call us cross-origin.
# Note: allow_credentials must be False when allow_origins=["*"] — the CORS spec
# forbids the combination. We use Bearer tokens (not cookies) so credentials=False is correct.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(movies.router, prefix=API_PREFIX)
app.include_router(halls.router, prefix=API_PREFIX)
app.include_router(showings.router, prefix=API_PREFIX)
app.include_router(bookings.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)


# ---- Error handlers ----

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": {"errors": exc.errors()},
            }
        },
    )


@app.get("/")
async def root():
    return {"name": "Movie Reservation API", "version": "0.2.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
