# Movie Reservation API — Phase 2

Full-stack implementation of the cinema seat reservation system designed in Phase 1.

- **Backend:** FastAPI + SQLAlchemy (async) + PostgreSQL + Redis
- **Frontend:** React + Vite (single-page app)
- **Containers:** Docker Compose runs db + redis + api

The Phase 1 ERD, API contract, and DECISIONS.md were followed exactly:

- Seat locking via Redis `SET NX EX` with a 5-minute TTL.
- Dynamic pricing computed at query time: `<50%` → base, `50–80%` → ×1.15, `>80%` → ×1.25, plus ×1.5 for VIP seats.
- Final price frozen onto `booking_seats.price_at_booking` at confirmation.
- Unique constraint on `booking_seats(showing_id, seat_id)` enforces no double booking at the DB level.

---

## How to run it

### 1. Start the backend (Postgres, Redis, FastAPI)

From the `Phase-2/` folder:

```bash
docker compose up --build
```

This brings up:

| Service | Port  | What |
|---------|-------|------|
| db      | 5432  | Postgres 15 (`cinema_db` / `cinema_user` / `cinema_pass`) |
| redis   | 6379  | Redis 7 |
| api     | 8000  | FastAPI (auto-reload) |

API root: http://localhost:8000  
Swagger docs: http://localhost:8000/docs

### 2. Seed the database

In a second terminal:

```bash
docker compose exec api python seed.py
```

This creates all tables and inserts:

- 1 admin user — **admin@cinema.com / admin1234**
- 3 sample movies
- 2 halls (Hall A: 10×10 — back row is VIP. Hall B: 8×12 — all standard)
- 2 upcoming showings

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

Vite proxies `/api` to `http://localhost:8000`, so the frontend and backend share an origin during development — no CORS issues.

---

## Project structure

```
Phase-2/
├── app/                    FastAPI backend
│   ├── main.py             entrypoint + error handler + CORS
│   ├── config.py           env vars
│   ├── database.py         async SQLAlchemy engine + session
│   ├── redis_client.py     async Redis client
│   ├── models.py           ORM models (matches ERD)
│   ├── schemas.py          Pydantic request/response schemas
│   ├── security.py         password hashing + JWT + role guards
│   ├── errors.py           shared error envelope
│   ├── routers/            one router per resource
│   │   ├── auth.py
│   │   ├── movies.py
│   │   ├── halls.py
│   │   ├── showings.py
│   │   └── bookings.py
│   └── services/
│       ├── pricing.py      dynamic price formula
│       └── holds.py        Redis seat-hold logic
├── frontend/               React SPA
│   ├── package.json
│   ├── vite.config.js      proxies /api to :8000
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js          all fetch() calls in one place
│       ├── index.css       color tokens + global styles
│       ├── components/     Navbar, MovieCard, SeatMap, BookingCard
│       └── pages/          Home, Showings, SeatSelection, MyBookings, Login, Register
├── seed.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Try the full flow

1. Visit http://localhost:5173 — see the seeded movies.
2. Click a movie → click a showing → opens the seat map.
3. **Register** a new customer account (or sign in).
4. Click some available (green) seats. The total updates as you go.
5. Click **Hold & Book** — the call sequence is `POST /showings/{id}/holds` then `POST /bookings`. You get a ticket code on success.
6. Go to **My Bookings** to view and cancel bookings.

### Admin actions

Admin accounts can't be registered through the UI (per Phase 1). The seed creates one. To call admin-only endpoints (`POST /movies`, `POST /halls`, `POST /showings`), use Swagger at http://localhost:8000/docs:

1. Hit `POST /auth/login` with `admin@cinema.com / admin1234`.
2. Copy the `access_token`.
3. Click the **Authorize** button (top right) and paste `Bearer <token>`.
4. Now you can create movies, halls, and showings.

---

## Verifying the dynamic pricing rule

Hit the seat map endpoint:

```bash
curl http://localhost:8000/api/v1/showings/1/seats
```

The response includes `occupancy_rate`, `pricing_tier` (`low`/`mid`/`high`), `tier_multiplier`, and a `price` for every seat. As more bookings come in, refresh the request — prices for the still-available seats will jump as occupancy crosses 50% and 80%.

---

## Environment variables

Copy `.env.example` to `.env` and edit if needed. The defaults work with docker compose out of the box. The important ones:

- `SECRET_KEY` — JWT signing secret. **Change this for production.**
- `HOLD_TTL_SECONDS` — Redis seat-hold TTL (default 300 = 5 min).
- `ACCESS_TOKEN_EXPIRE_MINUTES` — JWT lifetime (default 60).

---

## What changes in later phases

- Phase 3: rate limiting (`slowapi`), stricter Pydantic validation, finer-grained role checks.
- Phase 4: GitHub Actions CI + deploy to Render.
