# Movie Reservation API — Phase 3 (Security overlay)

Phase 3 is **not** a standalone application — it is a *security overlay* on
[Phase-2](../Phase-2). It contains only the files that change between
Phase 2 and Phase 3; the rest of the code (models, database, Redis, frontend,
Dockerfile, seed script, etc.) is reused from Phase 2 as-is.

This is intentional:

- Phase 2 already builds the working backend + frontend with seat holds and
  dynamic pricing.
- Phase 3 only adds **JWT hardening + RBAC + strict Pydantic validation +
  rate limiting** — about a dozen files.
- Duplicating Phase 2 to apply those changes would be pure redundancy.

Full security write-up: **[SECURITY.md](SECURITY.md)**.

---

## What's in this folder

```
Phase-3/
├── SECURITY.md             full Phase-3 security write-up + threat model
├── README.md               this file
├── apply.ps1               one-shot script: overlay these files onto Phase-2
├── requirements.txt        Phase-2 deps + slowapi
├── .env.example            adds APP_ENV, JWT_ISSUER/AUDIENCE, RATE_LIMIT_*, CORS_ORIGINS
└── app/
    ├── main.py             + slowapi middleware, 429 handler, security headers, CORS allowlist
    ├── config.py           + APP_ENV check, JWT iss/aud, rate-limit knobs, CORS_ORIGINS
    ├── security.py         + iss/aud/jti claims, single opaque error on token failure
    ├── schemas.py          rewritten: StrictModel (extra="forbid"), enums, regex, bounds, password policy
    ├── rate_limit.py       NEW: slowapi Limiter with user-id-aware key_func
    └── routers/
        ├── auth.py         + per-route limits on /register and /login
        ├── showings.py     + per-route limit on /holds
        └── bookings.py     + per-route limit on /bookings
```

Everything else (`models.py`, `database.py`, `redis_client.py`, `errors.py`,
`services/`, `routers/movies.py`, `routers/halls.py`, `frontend/`, `seed.py`,
`Dockerfile`, `docker-compose.yml`, …) **is reused from Phase-2 unchanged**.

---

## How to run Phase 3

Overlay these files on top of Phase-2 and start the Phase-2 docker stack:

```powershell
# From the Movie-Reservation-API/ folder
Copy-Item -Recurse -Force Phase-3\* Phase-2\
cd Phase-2
docker compose up --build -d
docker compose exec api python seed.py
```

A one-liner script does the same:

```powershell
.\Phase-3\apply.ps1
```

Then everything in **[SECURITY.md](SECURITY.md) section 0–5** works against
`http://localhost:8000`.

> If you want to keep a clean Phase-2 snapshot, commit Phase-2 before applying
> the overlay and revert with `git checkout -- Phase-2/` afterwards.

---

## Why this layout

The brief describes Phase 3 as *adding* JWT, RBAC, validation, and rate
limiting on top of the Phase 2 build. This folder is exactly that delta —
nothing more, nothing less. The Phase-2 folder remains the canonical
"working backend" snapshot; Phase-3 is the patch that makes it secure.
