"""
FastAPI entrypoint (Phase 3).

Adds, on top of Phase 2:
  - slowapi rate limiting middleware + 429 handler emitting our error envelope
  - CORS_ORIGINS read from config (no more `*` in production)
  - X-Content-Type-Options / X-Frame-Options / Referrer-Policy security headers
"""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import API_PREFIX, CORS_ORIGINS
from app.rate_limit import limiter
from app.routers import auth, movies, halls, showings, bookings


app = FastAPI(
    title="Movie Reservation API",
    version="0.3.0",
    description="Phase 3 - JWT auth, RBAC, validation, rate limiting.",
)

# ---- Rate limiter ----
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# ---- Routers ----
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(movies.router, prefix=API_PREFIX)
app.include_router(halls.router, prefix=API_PREFIX)
app.include_router(showings.router, prefix=API_PREFIX)
app.include_router(bookings.router, prefix=API_PREFIX)


# ---- Error handlers (Phase-1 envelope) ----

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
    # Pydantic v2 may put the raw ValueError object in each error's `ctx`,
    # which JSONResponse can't serialize on its own. jsonable_encoder handles it.
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": {"errors": jsonable_encoder(exc.errors())},
            }
        },
    )


@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Slow down and try again later.",
                "details": {"limit": str(exc.detail)},
            }
        },
        headers={"Retry-After": "60"},
    )


@app.get("/")
async def root():
    return {"name": "Movie Reservation API", "version": "0.3.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
