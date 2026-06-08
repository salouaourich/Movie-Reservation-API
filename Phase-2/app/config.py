"""
Central configuration. Reads environment variables and exposes them as
typed module-level constants used everywhere in the app.

Phase-3 additions:
  - APP_ENV ("dev" | "prod") drives stricter checks in prod
  - JWT_ISSUER / JWT_AUDIENCE bound into every token
  - RATE_LIMIT_* knobs for the slowapi middleware
  - SECRET_KEY hardened: refuse to boot in prod with the default value
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "dev").lower()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cinema_user:cinema_pass@localhost:5432/cinema_db",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ---- JWT ----
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "movie-reservation-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "movie-reservation-clients")

# Fail loudly in production if the secret was never rotated from the dev default.
if APP_ENV == "prod" and SECRET_KEY in ("changeme", "", None):
    sys.stderr.write(
        "FATAL: APP_ENV=prod but SECRET_KEY is unset or default. Refusing to start.\n"
    )
    raise SystemExit(1)
if APP_ENV == "prod" and len(SECRET_KEY) < 32:
    sys.stderr.write("FATAL: SECRET_KEY must be >= 32 chars in production.\n")
    raise SystemExit(1)

# ---- Seat hold TTL (5 minutes per DECISIONS.md) ----
HOLD_TTL_SECONDS = int(os.getenv("HOLD_TTL_SECONDS", "300"))

# ---- Rate limiting (slowapi) ----
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
# Sensible defaults; can be overridden per-environment.
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "10/minute")
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "5/minute")
RATE_LIMIT_BOOKING = os.getenv("RATE_LIMIT_BOOKING", "20/minute")
RATE_LIMIT_HOLD = os.getenv("RATE_LIMIT_HOLD", "30/minute")

# ---- CORS ----
# Comma-separated list of allowed origins (e.g. "https://my-frontend.onrender.com")
_cors_raw = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]

API_PREFIX = "/api/v1"
