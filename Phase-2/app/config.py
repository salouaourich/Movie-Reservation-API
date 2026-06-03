"""
Central configuration. Reads environment variables and exposes them as
typed module-level constants used everywhere in the app.
"""

import os
from dotenv import load_dotenv

# Load .env if present (for local non-docker runs)
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cinema_user:cinema_pass@localhost:5432/cinema_db",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Seat hold TTL (5 minutes per DECISIONS.md)
HOLD_TTL_SECONDS = int(os.getenv("HOLD_TTL_SECONDS", "300"))

# Payment: pending bookings expire after 15 minutes if not paid
PAYMENT_EXPIRE_MINUTES = int(os.getenv("PAYMENT_EXPIRE_MINUTES", "15"))

# Stripe
STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")

API_PREFIX = "/api/v1"
