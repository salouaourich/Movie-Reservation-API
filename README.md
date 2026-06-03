# 🎬 Movie Reservation System API

A full-stack cinema seat reservation backend built with **FastAPI**, **PostgreSQL**, and **Redis** — featuring dynamic demand-based pricing, JWT authentication, role-based access control, and a React frontend.

> **Live URLs**
> | Service | URL |
> |---------|-----|
> | 🌐 Frontend | https://cinema-frontend-11qu.onrender.com |
> | ⚡ API | https://cinema-api-5mey.onrender.com |
> | 📖 API Docs (Swagger) | https://cinema-api-5mey.onrender.com/docs |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.115 + Python 3.11 |
| Database | PostgreSQL 15 (SQLAlchemy async) |
| Cache / Locks | Redis 7 (asyncpg + seat holds) |
| Auth | JWT (python-jose) + bcrypt |
| Rate limiting | slowapi |
| Frontend | React 18 + Vite |
| Containers | Docker + Docker Compose |
| CI | GitHub Actions |
| Deploy | Render (free tier) + Upstash Redis |

---

## Project Structure

```
Movie-Reservation-API/
├── Phase-1/        Design — ERD, API contract, DECISIONS.md
├── Phase-2/        Build  — full FastAPI backend + React frontend
├── Phase-3/        Secure — JWT, RBAC, validation, rate limiting (overlay)
└── Phase-4/        Deploy — production Dockerfile, render.yaml, CI
```

> **How overlays work:** Phase-3 and Phase-4 contain only the files that differ
> from Phase-2. Running `.\Phase-3\apply.ps1` merges the security layer into
> Phase-2. The `deploy` branch on GitHub holds the final merged, runnable app.

---

## Branch Guide

| Branch | Contains | Purpose |
|--------|----------|---------|
| `main` | This README + docs | Project landing page |
| `Phase-1` | ERD, API contract, DECISIONS.md | Design deliverables |
| `Phase-2` | Full backend + frontend | Working app |
| `Phase-3` | Security overlay (13 files) | JWT, RBAC, validation, rate limits |
| `Phase-4` | Deploy overlay (Dockerfile, render.yaml, CI) | Production packaging |
| `deploy` | Combined runnable app | What Render deploys |

---

## Core Features

### 🎟 Seat Reservation Flow
1. Browse movies and showings
2. View the seat map with live dynamic prices
3. Hold seats (Redis TTL lock — 5 minutes)
4. Confirm booking (atomic DB commit)
5. Receive an e-ticket with QR payload

### 💰 Dynamic Seat Pricing
Prices are calculated at query time based on current occupancy:

| Occupancy | Multiplier | Tier |
|-----------|-----------|------|
| < 50% | × 1.00 | `low` |
| 50% – 80% | × 1.15 | `mid` |
| > 80% | × 1.25 | `high` |

VIP seats carry an additional × 1.5 multiplier on top of the tier price.

### 🔒 Security (Phase 3)
- JWT tokens with `iss`, `aud`, `jti` claims
- Role-based access: `admin` vs `customer`
- Pydantic strict validation (`extra="forbid"` on all request bodies)
- Rate limiting: 10/min login, 5/min register, 30/min holds, 20/min bookings

---

## Quick Start (local)

```powershell
# 1. Apply security overlay onto the working backend
cd Movie-Reservation-API
.\Phase-3\apply.ps1

# 2. Start the stack
cd Phase-2
docker compose up --build -d
docker compose exec api python seed.py

# 3. Start the frontend
cd frontend
npm install && npm run dev
```

| URL | What |
|-----|------|
| http://localhost:5173 | React frontend |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

**Admin credentials:** `admin@cinema.com` / `admin1234`

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | — | Register customer |
| POST | `/api/v1/auth/login` | — | Login → JWT |
| GET | `/api/v1/auth/me` | ✅ | Current user |
| GET | `/api/v1/movies` | — | List movies |
| POST | `/api/v1/movies` | Admin | Create movie |
| GET | `/api/v1/showings/{id}/seats` | — | Seat map + live prices |
| POST | `/api/v1/showings/{id}/holds` | Customer | Hold seats (Redis TTL) |
| POST | `/api/v1/bookings` | Customer | Confirm booking |
| GET | `/api/v1/bookings/me` | Customer | Booking history |
| GET | `/api/v1/bookings/{id}/ticket` | Customer | E-ticket |
| DELETE | `/api/v1/bookings/{id}` | Customer/Admin | Cancel booking |

Full contract: [`Phase-1/APIcontact.md`](Phase-1/APIcontact.md)

---

## Key Design Decisions

See [`Phase-1/DECISIONS.md`](Phase-1/DECISIONS.md) for full rationale. Summary:

- **Seat locking strategy:** Redis `SET NX EX` for the 5-min hold window. The DB `UniqueConstraint(showing_id, seat_id)` is the final anti-double-booking guard — even if two users race past Redis, the database rejects the second insert.
- **Pricing:** Computed at query time, never cached. The price a user sees on the seat map is the price they pay — frozen into `booking_seats.price_at_booking` at confirmation.
- **Auth:** HS256 JWT with `iss`/`aud` validation. `APP_ENV=prod` refuses to boot with a weak secret key.

---

## Deployment

See [`Phase-4/DEPLOYMENT.md`](Phase-4/DEPLOYMENT.md) for the full Render + Upstash guide.

CI runs on every push: lint → import smoke test → Docker build → frontend build.
