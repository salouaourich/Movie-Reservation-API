"""
Auth router: register a customer, login, and get the current user.
Admin accounts are seeded by seed.py - never via /auth/register.

Phase-3 additions:
  - Per-route rate limits on register / login (anti brute-force)
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import RATE_LIMIT_LOGIN, RATE_LIMIT_REGISTER
from app.database import get_db
from app.errors import APIError
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserPublic,
)
from app.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise APIError(409, "EMAIL_EXISTS", "An account with this email already exists.")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="customer",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise APIError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")

    token, expires_in = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return user
