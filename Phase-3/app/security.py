"""
Password hashing and JWT helpers, plus FastAPI dependencies that load the
current user out of an Authorization: Bearer <jwt> header.

Phase-3 hardening:
  - JWT now carries `iss` and `aud`, validated on decode
  - `jti` (random token id) and `iat` included to support future blacklisting
  - 401 vs. 403 split: missing/invalid token = 401; wrong role = 403
  - Single error message on token failure (no oracle for attackers)
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ISSUER,
    JWT_AUDIENCE,
)
from app.database import get_db
from app.errors import APIError
from app.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    """Return (token, seconds_until_expiry)."""
    expire_seconds = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(seconds=expire_seconds),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire_seconds


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the bearer token and return the matching User row, or raise 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise APIError(401, "UNAUTHENTICATED", "Missing or invalid Authorization header.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise APIError(401, "INVALID_TOKEN", "Token is invalid or expired.")

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise APIError(401, "INVALID_TOKEN", "Token is invalid or expired.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise APIError(401, "INVALID_TOKEN", "Token is invalid or expired.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise APIError(403, "FORBIDDEN", "Admin role required.")
    return user


async def require_customer(user: User = Depends(get_current_user)) -> User:
    if user.role != "customer":
        raise APIError(403, "FORBIDDEN", "Customer role required.")
    return user
