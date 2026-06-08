"""
Rate-limiting setup (Phase 3).

We use `slowapi` (built on `limits`) because it has zero infra requirements
in dev (in-memory backend) and can be pointed at Redis in production via
RATELIMIT_STORAGE_URI without touching application code.

Identity strategy:
  - Authenticated user  -> rate-limit by user id (sub in JWT)
  - Anonymous request   -> rate-limit by remote IP
This stops one attacker from creating many anonymous "users" to share quota,
while still protecting login/register endpoints (which have no user yet) by IP.
"""

from typing import Optional

from fastapi import Request
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import (
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_ENABLED,
    SECRET_KEY,
    ALGORITHM,
    JWT_ISSUER,
    JWT_AUDIENCE,
)


def _identify(request: Request) -> str:
    """Return a stable key for the requester."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=_identify,
    default_limits=[RATE_LIMIT_DEFAULT] if RATE_LIMIT_ENABLED else [],
    enabled=RATE_LIMIT_ENABLED,
    # Header injection is OFF on purpose: slowapi 0.1.9's _inject_headers
    # requires every decorated handler to either return a starlette Response
    # or declare a `response: Response` parameter. Our handlers return
    # Pydantic models, so we disable header injection and rely on
    # Retry-After in the 429 handler in main.py instead.
    headers_enabled=False,
)
