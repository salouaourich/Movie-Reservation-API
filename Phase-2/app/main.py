"""
FastAPI entrypoint.

- Mounts every router under /api/v1
- Installs a global exception handler that re-shapes errors to:
    { "error": { "code": ..., "message": ..., "details": ... } }
- Enables CORS so the React dev server on :5173 can call this API
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import API_PREFIX
from app.routers import auth, movies, halls, showings, bookings


app = FastAPI(
    title="Movie Reservation API",
    version="0.2.0",
    description="Phase 2 — Cinema seat booking with dynamic pricing.",
)

# Allow the React frontend (Vite dev server) to call us during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(movies.router, prefix=API_PREFIX)
app.include_router(halls.router, prefix=API_PREFIX)
app.include_router(showings.router, prefix=API_PREFIX)
app.include_router(bookings.router, prefix=API_PREFIX)


# ---- Error handlers: enforce the Phase-1 error envelope everywhere ----

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # If our APIError already shaped the detail, just pass it through.
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    # Otherwise, wrap whatever the default FastAPI/Starlette message was.
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
