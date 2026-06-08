# Movie Reservation System — Full Project Documentation

**Author:** Saloua Ourich  
**Stack:** FastAPI · PostgreSQL · Redis · React · Docker  
**Live API:** https://cinema-api-5mey.onrender.com/docs  
**Live Frontend:** https://cinema-frontend-11qu.onrender.com  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Database Design](#5-database-design)
6. [Authentication & Security](#6-authentication--security)
7. [Dynamic Pricing Engine](#7-dynamic-pricing-engine)
8. [Seat Hold Mechanism](#8-seat-hold-mechanism)
9. [API Reference](#9-api-reference)
10. [Error Handling](#10-error-handling)
11. [Rate Limiting](#11-rate-limiting)
12. [Configuration & Environment Variables](#12-configuration--environment-variables)
13. [Running Locally](#13-running-locally)
14. [Frontend Overview](#14-frontend-overview)
15. [Deployment](#15-deployment)
16. [Key Design Decisions](#16-key-design-decisions)

---

## 1. Project Overview

The **Movie Reservation System** is a full-stack cinema seat-booking backend built as a phased project. It allows customers to browse movies, view live seat maps with dynamic pricing, hold seats temporarily, and confirm bookings — while giving administrators full control over movies, halls, and showings.

### Core capabilities

| Capability | Description |
|---|---|
| Movie catalog | Browse, search, and filter movies by genre |
| Seat reservation | Select seats on a live seat map and hold them for 5 minutes |
| Dynamic pricing | Ticket price rises automatically as seats fill up |
| JWT authentication | Secure login with role-based access (admin / customer) |
| E-tickets | Each confirmed booking generates a unique ticket code |
| Booking history | Customers can view and cancel their own bookings |
| Admin panel | Admins can manage movies, halls, and showings |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│                                                                 │
│    React 18 + Vite (SPA)          Swagger UI (/docs)           │
│    http://localhost:5173           http://localhost:8000/docs   │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP / REST (JSON)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                        │
│                                                                 │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │   Auth   │ │ Movies │ │  Halls   │ │ Showings │ │Bookings│ │
│  │  Router  │ │ Router │ │  Router  │ │  Router  │ │ Router │ │
│  └──────────┘ └────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │  Pricing Service│    │       Holds Service              │   │
│  │  (occupancy →   │    │   (Redis SET NX EX, TTL=300s)    │   │
│  │   multiplier)   │    │                                  │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────┐   ┌──────────────────────────────┐   │
│  │   JWT Security Layer │   │    Rate Limiter (slowapi)    │   │
│  │ (HS256, iss/aud/jti) │   │    per-route IP/user limits  │   │
│  └──────────────────────┘   └──────────────────────────────┘   │
└───────────┬─────────────────────────────┬───────────────────────┘
            │  asyncpg (async SQL)        │  redis-py (async)
            ▼                             ▼
┌─────────────────────┐       ┌───────────────────────┐
│  PostgreSQL 15      │       │      Redis 7           │
│                     │       │                        │
│  users              │       │  hold:showing:{id}:    │
│  movies             │       │    seat:{id}  → user_id│
│  halls              │       │    (TTL = 300s)        │
│  seats              │       │                        │
│  showings           │       └───────────────────────┘
│  bookings           │
│  booking_seats      │
└─────────────────────┘
```

### Request lifecycle (seat booking)

```
1. Customer browses movies                     GET /movies
2. Picks a movie and gets its showings         GET /movies/{id}/showings
3. Opens the seat map (live prices shown)      GET /showings/{id}/seats
4. Holds selected seats (5-min timer starts)   POST /showings/{id}/holds
5. Confirms the booking                        POST /bookings
6. Retrieves e-ticket                          GET /bookings/{id}/ticket
```

---

## 3. Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Backend framework | FastAPI | 0.115.0 | Async HTTP API, auto OpenAPI docs |
| ASGI server | Uvicorn | 0.30.6 | Runs the FastAPI app |
| ORM | SQLAlchemy (async) | 2.0.35 | Database models and queries |
| DB driver | asyncpg | 0.29.0 | Async PostgreSQL driver |
| Database | PostgreSQL | 15 | Persistent data storage |
| Cache / locks | Redis | 7 (redis-py 5.0.8) | Seat hold TTL locks |
| Auth | python-jose + passlib | 3.3.0 / 1.7.4 | JWT creation/validation, bcrypt hashing |
| Validation | Pydantic v2 | 2.9.2 | Request/response schemas, strict mode |
| Rate limiting | slowapi | 0.1.9 | Per-route IP/user request limits |
| Migrations | Alembic | 1.13.3 | Database schema migrations |
| Frontend | React 18 + Vite | 18 / 5 | Single-page application |
| Containers | Docker + Docker Compose | — | Local development and production |
| CI | GitHub Actions | — | Lint, build, smoke tests |
| Deploy | Render + Upstash Redis | — | Cloud hosting |

---

## 4. Project Structure

The project was built in **4 phases**, each building on the previous one:

```
Movie-Reservation-API/
│
├── Phase-1/               Design phase
│   ├── ERD.png            Entity-Relationship Diagram
│   ├── API_CONTRACT.md    Full endpoint specification
│   └── DECISIONS.md       Architectural decisions log
│
├── Phase-2/               Build phase — working application
│   ├── app/
│   │   ├── main.py        FastAPI app entrypoint, middleware
│   │   ├── config.py      Environment variables / settings
│   │   ├── database.py    Async DB engine and session factory
│   │   ├── models.py      SQLAlchemy ORM models
│   │   ├── schemas.py     Pydantic v2 request/response schemas
│   │   ├── security.py    JWT helpers, password hashing, auth deps
│   │   ├── errors.py      Unified APIError exception class
│   │   ├── redis_client.py Redis connection
│   │   ├── rate_limit.py  slowapi limiter instance
│   │   ├── routers/
│   │   │   ├── auth.py    Register, login, /me
│   │   │   ├── movies.py  CRUD for movies
│   │   │   ├── halls.py   Hall + seat management
│   │   │   ├── showings.py Showings + seat map + holds
│   │   │   ├── bookings.py Booking create/list/cancel/ticket
│   │   │   └── payments.py Stripe payment intent (future)
│   │   └── services/
│   │       ├── pricing.py Dynamic pricing logic
│   │       └── holds.py   Redis seat hold operations
│   ├── frontend/          React 18 + Vite SPA
│   ├── seed.py            Database seeder (movies, halls, showings)
│   ├── requirements.txt   Python dependencies
│   ├── Dockerfile         API container definition
│   └── docker-compose.yml Local stack (api + db + redis)
│
├── Phase-3/               Security overlay
│   ├── app/               Hardened schemas + security + rate limits
│   └── apply.ps1          Merges Phase-3 files into Phase-2
│
├── Phase-4/               Deployment overlay
│   ├── Dockerfile         Production-ready image
│   └── render.yaml        Render.com service definitions
│
├── Dockerfile             Root-level production Dockerfile
├── render.yaml            Render deployment config
└── README.md              Project summary
```

### How overlays work

Phase-3 and Phase-4 contain **only the files that changed** from Phase-2. Running `.\Phase-3\apply.ps1` copies those files into the Phase-2 directory. The `deploy` branch on GitHub contains the fully merged, production-ready application.

---

## 5. Database Design

### Entity-Relationship Overview

```
users ──────────< bookings >────────── showings >────────── movies
                     │                     │
                     │                     └── halls ───< seats
                     │
                 booking_seats >──────────── seats
```

### Tables

#### `users`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | Auto-increment primary key |
| email | VARCHAR(255) | UNIQUE, NOT NULL, INDEX | Login identifier |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash |
| full_name | VARCHAR(255) | NOT NULL | Display name |
| role | VARCHAR(20) | NOT NULL, default='customer' | `customer` or `admin` |
| created_at | DATETIME | NOT NULL | Registration timestamp |

#### `movies`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | — |
| title | VARCHAR(255) | NOT NULL, INDEX | Movie title |
| description | TEXT | nullable | Plot summary |
| duration_minutes | INTEGER | NOT NULL | Used for showing overlap detection |
| genre | VARCHAR(50) | nullable, INDEX | e.g. `sci-fi`, `action` |
| rating | VARCHAR(10) | nullable | `G`, `PG`, `PG-13`, `R`, `NC-17` |
| poster_url | TEXT | nullable | URL or base64 data URI |
| is_active | BOOLEAN | NOT NULL, default=true | Soft-delete flag |
| created_at | DATETIME | — | — |

#### `halls`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | — |
| name | VARCHAR(100) | UNIQUE, NOT NULL | e.g. `Hall A`, `IMAX` |
| rows_count | INTEGER | NOT NULL | Number of rows |
| cols_count | INTEGER | NOT NULL | Seats per row |
| created_at | DATETIME | — | — |

#### `seats`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | — |
| hall_id | INTEGER | FK(halls), INDEX | Parent hall |
| row_label | VARCHAR(5) | NOT NULL | e.g. `A`, `B`, `AA` |
| seat_number | INTEGER | NOT NULL | Position within row |
| seat_type | VARCHAR(20) | default='standard' | `standard` or `vip` |
| — | — | UNIQUE(hall_id, row_label, seat_number) | No duplicate seats in hall |

#### `showings`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | — |
| movie_id | INTEGER | FK(movies), INDEX | — |
| hall_id | INTEGER | FK(halls), INDEX | — |
| start_time | DATETIME | NOT NULL, INDEX | Show time (must be future on create) |
| base_price | NUMERIC(10,2) | NOT NULL | Starting ticket price |
| status | VARCHAR(20) | default='scheduled' | `scheduled`, `cancelled`, `completed` |
| created_at | DATETIME | — | — |

#### `bookings`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | — |
| user_id | INTEGER | FK(users), INDEX | Owner |
| showing_id | INTEGER | FK(showings), INDEX | Which showing |
| status | VARCHAR(20) | default='pending_payment' | `confirmed` or `cancelled` |
| ticket_code | VARCHAR(50) | UNIQUE, INDEX | e.g. `TKT-7G2K-9XW1` |
| total_price | NUMERIC(10,2) | NOT NULL | Sum of all seat prices at booking time |
| payment_intent_id | VARCHAR(100) | nullable | Stripe PaymentIntent ID |
| payment_expires_at | DATETIME | nullable | Auto-cancellation deadline |
| created_at | DATETIME | — | — |
| cancelled_at | DATETIME | nullable | Populated on cancellation |

#### `booking_seats`
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | INTEGER | PK | — |
| booking_id | INTEGER | FK(bookings, CASCADE) | Parent booking |
| showing_id | INTEGER | FK(showings), INDEX | Redundant FK for query efficiency |
| seat_id | INTEGER | FK(seats) | The reserved seat |
| price_at_booking | NUMERIC(10,2) | NOT NULL | Frozen price — never changes |
| — | — | UNIQUE(showing_id, seat_id) | **Prevents double booking at DB level** |

> The `UNIQUE(showing_id, seat_id)` constraint on `booking_seats` is the final safety net. Even if two requests race through Redis simultaneously, the database will reject the second `INSERT` with an `IntegrityError`, which the API converts to a `409 SEAT_UNAVAILABLE` response.

---

## 6. Authentication & Security

### Authentication flow

```
Client                              API
  │                                  │
  │──── POST /auth/login ───────────►│
  │     { email, password }          │  1. Look up user by email
  │                                  │  2. bcrypt.verify(password, hash)
  │◄─── 200 { access_token } ───────│  3. Create HS256 JWT
  │                                  │
  │──── GET /auth/me ───────────────►│
  │     Authorization: Bearer <jwt>  │  1. Decode JWT (verify iss, aud, exp)
  │                                  │  2. Load user from DB by sub (user_id)
  │◄─── 200 { id, email, role } ────│
```

### JWT token structure

```json
{
  "sub": "7",
  "role": "customer",
  "iss": "movie-reservation-api",
  "aud": "movie-reservation-clients",
  "iat": 1747000000,
  "exp": 1747003600,
  "jti": "a1b2c3d4e5f6..."
}
```

| Claim | Purpose |
|---|---|
| `sub` | User ID — used to load the user from DB |
| `role` | Checked for RBAC (`admin` vs `customer`) |
| `iss` | Issuer — validated on every decode |
| `aud` | Audience — validated on every decode |
| `iat` | Issued-at timestamp |
| `exp` | Expiry (default: 60 minutes) |
| `jti` | Unique token ID — enables future blacklisting |

### Role-based access control (RBAC)

| Dependency | Allowed | Used on |
|---|---|---|
| `get_current_user` | Any authenticated user | `/auth/me`, booking detail |
| `require_admin` | `role == "admin"` only | Movie CRUD, hall CRUD, showing create |
| `require_customer` | `role == "customer"` only | Hold seats, create bookings |

> Admin accounts are only created via `seed.py`. The `/auth/register` endpoint always creates `customer` accounts.

### Password policy (Phase 3)

Enforced at registration via a Pydantic `field_validator`:
- Minimum 8 characters, maximum 128
- At least one **lowercase** letter
- At least one **uppercase** letter
- At least one **digit**

### Security headers

Every HTTP response includes:

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Referrer-Policy` | `no-referrer` | Don't leak URL in Referer header |

### Production safeguards

The app **refuses to start** in production (`APP_ENV=prod`) if:
- `SECRET_KEY` is the default value `"changeme"`
- `SECRET_KEY` is shorter than 32 characters

---

## 7. Dynamic Pricing Engine

One of the core features of this system is **demand-based seat pricing**. Prices update in real time as seats fill up — the same mechanism used by airlines and ride-sharing apps.

### Pricing formula

```
final_price = base_price × tier_multiplier × vip_multiplier
```

### Occupancy tiers

| Occupancy | Tier | Multiplier | Example (base = $50) |
|---|---|---|---|
| < 50% | `low` | × 1.00 | $50.00 |
| 50% – 80% | `mid` | × 1.15 | $57.50 |
| > 80% | `high` | × 1.25 | $62.50 |

### VIP seat surcharge

VIP seats carry an **additional × 1.5 multiplier** applied on top of the tier price:

| Tier | Standard price | VIP price |
|---|---|---|
| low | $50.00 | $75.00 |
| mid | $57.50 | $86.25 |
| high | $62.50 | $93.75 |

### Implementation

```python
# app/services/pricing.py

def pricing_tier(occupancy_rate: float) -> tuple[str, Decimal]:
    if occupancy_rate < 0.5:
        return "low", Decimal("1.00")
    if occupancy_rate <= 0.8:
        return "mid", Decimal("1.15")
    return "high", Decimal("1.25")

def calculate_seat_price(base_price, occupancy_rate, seat_type) -> Decimal:
    _, multiplier = pricing_tier(occupancy_rate)
    price = Decimal(base_price) * multiplier
    if seat_type == "vip":
        price = price * Decimal("1.5")
    return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### Price integrity guarantee

- Prices are computed **at query time** — never cached, never pre-stored.
- When a booking is confirmed, the price at that exact moment is **frozen** into `booking_seats.price_at_booking`.
- The customer always pays the price they saw on the seat map.

---

## 8. Seat Hold Mechanism

To prevent two users from booking the same seat simultaneously, the system uses a **Redis-based seat hold** with a 5-minute TTL (Time To Live).

### Redis key structure

```
hold:showing:{showing_id}:seat:{seat_id}  →  value: user_id  (TTL: 300 seconds)
```

### Hold lifecycle

```
User selects seats
      │
      ▼
POST /showings/{id}/holds
      │
      ├─ For each seat: Redis SET NX EX 300
      │    NX = only set if key doesn't exist
      │    EX = expire after 300 seconds
      │
      ├─ If ANY seat is already held → roll back ALL acquired holds → return 409
      │
      └─ All seats acquired → return { expires_at, ttl_seconds: 300 }
                                          │
                            5 minutes max │
                                          ▼
                              POST /bookings  (confirm)
                                    │
                                    ├─ Verify user still owns ALL holds
                                    ├─ INSERT into booking_seats (DB unique constraint)
                                    ├─ COMMIT transaction
                                    └─ DELETE Redis holds (DB is now source of truth)
```

### Key properties

| Property | Behavior |
|---|---|
| **Atomic acquisition** | All-or-nothing: if seat 3 of 4 is taken, none are held |
| **TTL expiry** | Holds auto-release after 300 seconds — no cleanup job needed |
| **Own-hold refresh** | Re-requesting a seat you already hold refreshes the TTL |
| **DB as final authority** | `UNIQUE(showing_id, seat_id)` on `booking_seats` is the true double-booking guard |
| **Race condition protection** | Even if two users bypass Redis simultaneously, the DB `IntegrityError` catches it |

---

## 9. API Reference

**Base URL (local):** `http://localhost:8000/api/v1`  
**Base URL (production):** `https://cinema-api-5mey.onrender.com/api/v1`  
**Authentication:** `Authorization: Bearer <jwt>` on protected routes  
**All prices:** Decimal with 2 decimal places  
**All timestamps:** ISO 8601 UTC  

---

### Authentication

#### `POST /auth/register`
Create a customer account. Admin accounts are created by the seeder only.

**Auth:** Public  
**Rate limit:** 5 requests/minute

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass1",
  "full_name": "John Doe"
}
```

**Response `201`:**
```json
{
  "id": 7,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "customer",
  "created_at": "2026-06-08T10:00:00Z"
}
```

**Errors:** `400` validation failed · `409` email already exists

---

#### `POST /auth/login`
Authenticate and receive a JWT access token.

**Auth:** Public  
**Rate limit:** 10 requests/minute

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass1"
}
```

**Response `200`:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors:** `401` invalid credentials

---

#### `GET /auth/me`
Returns the currently authenticated user's profile.

**Auth:** Required (any role)

**Response `200`:**
```json
{
  "id": 7,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "customer"
}
```

---

### Movies

#### `GET /movies`
List all active movies. Supports pagination, search, and genre filtering.

**Auth:** Public  
**Query params:**

| Param | Type | Default | Description |
|---|---|---|---|
| `genre` | string | — | Filter by genre (exact match) |
| `search` | string | — | Search in title (case-insensitive) |
| `page` | int | 1 | Page number (≥ 1) |
| `page_size` | int | 20 | Results per page (1–100) |

**Response `200`:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Dune Part Three",
      "description": "The saga continues...",
      "duration_minutes": 165,
      "genre": "sci-fi",
      "rating": "PG-13",
      "poster_url": "https://example.com/poster.jpg",
      "is_active": true
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 45
}
```

---

#### `GET /movies/{movie_id}`
Get a single movie by ID.

**Auth:** Public  
**Errors:** `404` not found

---

#### `POST /movies`
Create a new movie.

**Auth:** Admin only

**Request body:**
```json
{
  "title": "Dune Part Three",
  "description": "The saga continues...",
  "duration_minutes": 165,
  "genre": "sci-fi",
  "rating": "PG-13",
  "poster_url": "https://example.com/poster.jpg"
}
```

**Field rules:**
- `title`: 1–255 chars, required
- `description`: max 4000 chars
- `duration_minutes`: 1–600
- `genre`: max 50 chars
- `rating`: one of `G`, `PG`, `PG-13`, `R`, `NC-17`
- `poster_url`: must start with `https://` or `http://`

**Response `201`:** Movie object  
**Errors:** `400` validation · `401` · `403`

---

#### `PATCH /movies/{movie_id}`
Partially update a movie. All fields optional.

**Auth:** Admin only  
**Response `200`:** Updated movie object  
**Errors:** `400` · `401` · `403` · `404`

---

#### `DELETE /movies/{movie_id}`
Soft-delete a movie (sets `is_active = false`). The movie disappears from customer listings but its data is preserved.

**Auth:** Admin only  
**Response `204`:** No content  
**Errors:** `401` · `403` · `404`

---

#### `GET /movies/{movie_id}/showings`
List all showings for a movie, with real-time occupancy data.

**Auth:** Public  
**Query params:** `?date=2026-06-08` (filter by date)

**Response `200`:**
```json
{
  "items": [
    {
      "id": 42,
      "movie_id": 1,
      "hall_id": 3,
      "hall_name": "Hall A",
      "start_time": "2026-06-08T20:30:00Z",
      "base_price": "50.00",
      "occupancy_rate": 0.62,
      "seats_total": 100,
      "seats_available": 38,
      "status": "scheduled"
    }
  ]
}
```

---

### Halls

#### `POST /halls`
Create a hall with auto-generated or manually specified seats.

**Auth:** Admin only

**Request body:**
```json
{
  "name": "Hall A",
  "rows_count": 10,
  "cols_count": 10,
  "seats": [
    { "row_label": "A", "seat_number": 1, "seat_type": "standard" },
    { "row_label": "A", "seat_number": 2, "seat_type": "vip" }
  ]
}
```

> If `seats` is omitted, the API auto-generates `rows_count × cols_count` standard seats labeled A1, A2 … J10.

**Response `201`:** Hall object with full seat list

---

#### `GET /halls`
List all halls.

**Auth:** Admin only  
**Response `200`:** Array of hall objects with seats

---

### Showings

#### `POST /showings`
Schedule a new showing. Validates that no other showing overlaps in the same hall (based on movie duration).

**Auth:** Admin only

**Request body:**
```json
{
  "movie_id": 1,
  "hall_id": 3,
  "start_time": "2026-07-01T20:30:00Z",
  "base_price": "50.00"
}
```

**Validation:**
- `start_time` must be in the future
- `base_price` must be positive, max $9999.99, max 2 decimal places
- No time overlap with existing showings in the same hall

**Response `201`:** Showing object  
**Errors:** `400` · `401` · `403` · `404` movie/hall not found · `409` time overlap

---

#### `GET /showings/{showing_id}`
Get a single showing.

**Auth:** Public  
**Errors:** `404`

---

#### `GET /showings/{showing_id}/seats`
**The dynamic pricing endpoint.** Returns the full seat map with real-time availability status and computed prices.

**Auth:** Public

**Response `200`:**
```json
{
  "showing_id": 42,
  "base_price": "50.00",
  "occupancy_rate": 0.62,
  "pricing_tier": "mid",
  "tier_multiplier": 1.15,
  "hall": {
    "id": 3,
    "name": "Hall A",
    "rows_count": 10,
    "cols_count": 10
  },
  "seats": [
    {
      "id": 301,
      "row_label": "A",
      "seat_number": 1,
      "seat_type": "standard",
      "status": "available",
      "price": "57.50"
    },
    {
      "id": 302,
      "row_label": "A",
      "seat_number": 2,
      "seat_type": "vip",
      "status": "booked",
      "price": "86.25"
    },
    {
      "id": 303,
      "row_label": "A",
      "seat_number": 3,
      "seat_type": "standard",
      "status": "held",
      "price": "57.50"
    }
  ]
}
```

**Seat statuses:**

| Status | Meaning |
|---|---|
| `available` | Free to hold/book |
| `held` | Another user is currently in checkout (Redis TTL lock) |
| `booked` | Permanently reserved in the database |

---

#### `POST /showings/{showing_id}/holds`
Atomically acquire holds on one or more seats. If **any** seat is unavailable, **none** are held.

**Auth:** Customer only  
**Rate limit:** 30 requests/minute

**Request body:**
```json
{ "seat_ids": [301, 304, 305] }
```

**Rules:**
- `seat_ids`: non-empty list, max 10 seats, no duplicates, all positive integers
- All seats must belong to this showing's hall
- All seats must be unbooked (DB check)

**Response `201`:**
```json
{
  "showing_id": 42,
  "held_seat_ids": [301, 304, 305],
  "expires_at": "2026-06-08T10:35:00Z",
  "ttl_seconds": 300
}
```

**Errors:** `400` invalid seats · `401` · `409` seats already held/booked

---

#### `DELETE /showings/{showing_id}/holds`
Release seat holds. Omit `seat_ids` to release all holds for this showing.

**Auth:** Customer only  
**Response `204`:** No content

---

### Bookings

#### `POST /bookings`
Confirm a booking. The caller must currently hold all specified seats. Prices are frozen at the moment of confirmation.

**Auth:** Customer only  
**Rate limit:** 20 requests/minute

**Request body:**
```json
{
  "showing_id": 42,
  "seat_ids": [301, 304, 305]
}
```

**Response `201`:**
```json
{
  "id": 88,
  "showing_id": 42,
  "user_id": 7,
  "status": "confirmed",
  "ticket_code": "TKT-7G2K-9XW1",
  "total_price": "172.50",
  "created_at": "2026-06-08T10:32:00Z",
  "seats": [
    { "seat_id": 301, "row_label": "A", "seat_number": 1, "price_at_booking": "57.50" },
    { "seat_id": 304, "row_label": "A", "seat_number": 4, "price_at_booking": "57.50" },
    { "seat_id": 305, "row_label": "A", "seat_number": 5, "price_at_booking": "57.50" }
  ]
}
```

**Errors:** `400` empty list · `401` · `409` hold missing/expired or seat just booked by another user

---

#### `GET /bookings/me`
List the authenticated customer's full booking history.

**Auth:** Customer only

**Response `200`:**
```json
{
  "items": [
    {
      "id": 88,
      "showing_id": 42,
      "movie_title": "Dune Part Three",
      "hall_name": "Hall A",
      "start_time": "2026-06-08T20:30:00Z",
      "status": "confirmed",
      "total_price": "172.50",
      "ticket_code": "TKT-7G2K-9XW1",
      "created_at": "2026-06-08T10:32:00Z"
    }
  ]
}
```

---

#### `GET /bookings/{booking_id}`
Get full booking detail. Only the booking owner or an admin can access this.

**Auth:** Owner or Admin  
**Response `200`:** Full booking object with seat detail  
**Errors:** `401` · `403` · `404`

---

#### `DELETE /bookings/{booking_id}`
Cancel a booking. Frees the seats back to `available`. Cannot cancel after the showing has started.

**Auth:** Owner or Admin

**Response `200`:**
```json
{
  "id": 88,
  "status": "cancelled",
  "cancelled_at": "2026-06-08T11:00:00Z"
}
```

**Errors:** `401` · `403` · `404` · `409` showing already started

---

#### `GET /bookings/{booking_id}/ticket`
Retrieve the e-ticket for a confirmed booking.

**Auth:** Owner or Admin

**Response `200`:**
```json
{
  "ticket_code": "TKT-7G2K-9XW1",
  "qr_payload": "TKT-7G2K-9XW1",
  "movie": {
    "title": "Dune Part Three",
    "duration_minutes": 165,
    "rating": "PG-13"
  },
  "showing": {
    "start_time": "2026-06-08T20:30:00Z",
    "hall_name": "Hall A"
  },
  "seats": [
    { "row_label": "A", "seat_number": 1, "seat_type": "standard" },
    { "row_label": "A", "seat_number": 4, "seat_type": "standard" }
  ],
  "total_price": "172.50",
  "issued_at": "2026-06-08T10:32:00Z"
}
```

**Errors:** `401` · `403` · `404` · `409` booking is cancelled

---

## 10. Error Handling

All error responses follow a consistent envelope format:

```json
{
  "error": {
    "code": "SEAT_UNAVAILABLE",
    "message": "Seats 301, 304 are already held by another user.",
    "details": { "seat_ids": [301, 304] }
  }
}
```

### Error codes

| HTTP Status | Code | When it happens |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Pydantic schema validation failed |
| 400 | `EMPTY_LIST` | `seat_ids` list was empty |
| 400 | `INVALID_SEATS` | Seat IDs don't belong to this hall |
| 401 | `UNAUTHENTICATED` | Missing or malformed `Authorization` header |
| 401 | `INVALID_TOKEN` | JWT expired, wrong signature, or user deleted |
| 403 | `FORBIDDEN` | Authenticated but wrong role or not the owner |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `EMAIL_EXISTS` | Registration email already in use |
| 409 | `SEAT_UNAVAILABLE` | Seat held by someone else or already booked |
| 409 | `HOLD_REQUIRED` | Trying to book without a valid hold |
| 409 | `SHOWING_STARTED` | Cannot cancel a booking for a showing already in progress |
| 409 | `TIME_OVERLAP` | New showing clashes with an existing one in the same hall |
| 429 | `RATE_LIMITED` | Too many requests; `Retry-After: 60` header included |
| 500 | `HTTP_ERROR` | Unexpected server error |

---

## 11. Rate Limiting

Rate limiting is implemented using **slowapi** (a FastAPI-native wrapper around limits). Limits are enforced per-IP for public endpoints and per-user for authenticated ones.

| Endpoint | Limit | Reason |
|---|---|---|
| `POST /auth/login` | 10 / minute | Brute-force protection |
| `POST /auth/register` | 5 / minute | Account spam prevention |
| `POST /bookings` | 20 / minute | Prevent booking abuse |
| `POST /showings/{id}/holds` | 30 / minute | Prevent hold-squatting |
| All others | 120 / minute | General DoS protection |

When a limit is exceeded, the API returns:
```
HTTP 429 Too Many Requests
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Slow down and try again later.",
    "details": { "limit": "10 per 1 minute" }
  }
}
```

All rate limit values can be overridden via environment variables (see Section 12).

---

## 12. Configuration & Environment Variables

All configuration is read from environment variables (with safe defaults for local development).

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `dev` | `dev` or `prod` — enables production hardening |
| `DATABASE_URL` | `postgresql+asyncpg://cinema_user:cinema_pass@localhost:5432/cinema_db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `SECRET_KEY` | `changeme` | JWT signing key — **must be changed in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime in minutes |
| `JWT_ISSUER` | `movie-reservation-api` | JWT `iss` claim |
| `JWT_AUDIENCE` | `movie-reservation-clients` | JWT `aud` claim |
| `HOLD_TTL_SECONDS` | `300` | Seat hold expiry time (5 minutes) |
| `RATE_LIMIT_LOGIN` | `10/minute` | Login rate limit |
| `RATE_LIMIT_REGISTER` | `5/minute` | Register rate limit |
| `RATE_LIMIT_BOOKING` | `20/minute` | Booking creation rate limit |
| `RATE_LIMIT_HOLD` | `30/minute` | Hold acquisition rate limit |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `STRIPE_SECRET_KEY` | *(empty)* | Stripe API key (future payments) |
| `STRIPE_PUBLISHABLE_KEY` | *(empty)* | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | *(empty)* | Stripe webhook signing secret |

> **Production requirement:** `APP_ENV=prod` with `SECRET_KEY=changeme` will crash on startup intentionally.

### Local `.env` file (optional)

Create `Phase-2/.env` to avoid passing environment variables manually:

```env
APP_ENV=dev
SECRET_KEY=my-local-dev-secret-key-here
DATABASE_URL=postgresql+asyncpg://cinema_user:cinema_pass@localhost:5432/cinema_db
REDIS_URL=redis://localhost:6379
```

---

## 13. Running Locally

### Prerequisites

| Tool | Version | Check |
|---|---|---|
| Docker Desktop | Latest | `docker --version` |
| Node.js | 18+ | `node -v` |
| PowerShell | 5.1+ | Already on Windows |

> **Important:** Docker Desktop must be **open and running** before any `docker` commands.

### Step 1 — Apply the security overlay

```powershell
cd "C:\Users\User\OneDrive\Desktop\Movie-Reservation-API"
.\Phase-3\apply.ps1
```

This copies the Phase-3 security-hardened files (JWT hardening, rate limits, strict validation) into the Phase-2 working directory.

> If PowerShell blocks the script: `Set-ExecutionPolicy RemoteSigned` (run as Administrator)

### Step 2 — Start the backend stack

```powershell
cd "C:\Users\User\OneDrive\Desktop\Movie-Reservation-API\Phase-2"
docker compose up --build -d
```

This starts three containers:
- `phase-2-api-1` — FastAPI on port 8000
- `phase-2-db-1` — PostgreSQL on port 5433
- `phase-2-redis-1` — Redis on port 6379

### Step 3 — Seed the database

```powershell
docker compose exec api python seed.py
```

Expected output:
```
✅ Seed complete.
   Admin     : admin@cinema.com / admin1234
   Movies    : 45
   Halls     : 4  (A 10×10, B 8×12, C 12×15 IMAX, D 6×8)
   Showings  : 225  (spread over 20 days, USD pricing)
```

### Step 4 — Start the frontend

```powershell
cd "C:\Users\User\OneDrive\Desktop\Movie-Reservation-API\Phase-2\frontend"
npm install
npm run dev
```

### Access URLs

| Service | URL | Credentials |
|---|---|---|
| React Frontend | http://localhost:5173 | Register or use admin below |
| Swagger API Docs | http://localhost:8000/docs | — |
| Health check | http://localhost:8000/health | — |
| Admin account | — | `admin@cinema.com` / `admin1234` |

### Stopping the stack

```powershell
cd "C:\Users\User\OneDrive\Desktop\Movie-Reservation-API\Phase-2"
docker compose down
```

### Troubleshooting

| Problem | Solution |
|---|---|
| `service "api" is not running` | Run `docker compose logs api` to see the error |
| `port is already allocated` | Another container is using port 8000. Run `docker ps` to find it and `docker stop <name>` |
| `ECONNREFUSED 127.0.0.1:8000` | The `api` container is not running. Start it with `docker compose up -d api` |
| PowerShell script blocked | Run `Set-ExecutionPolicy RemoteSigned` as Administrator |
| Frontend blank / errors | Ensure the API is running first, then hard-refresh the browser |

---

## 14. Frontend Overview

The frontend is a **React 18 + Vite** single-page application located at `Phase-2/frontend/`.

### Structure

```
frontend/
├── src/
│   ├── main.jsx          App entry point
│   ├── App.jsx           Routing and layout
│   ├── api.js            Axios API client (base URL, auth headers)
│   ├── index.css         Global styles
│   ├── components/       Reusable UI components
│   └── pages/            Route-level page components
└── vite.config.js        Vite config (includes API proxy)
```

### API proxy

Vite proxies all `/api/v1/*` requests to `http://localhost:8000` during development. This means the frontend never needs CORS headers locally — all requests appear same-origin.

### Key pages

| Page | Path | Description |
|---|---|---|
| Home | `/` | Movie listing with search and genre filter |
| Movie detail | `/movies/:id` | Showings list for a movie |
| Seat map | `/showings/:id/seats` | Live seat map with dynamic pricing |
| Checkout | `/checkout` | Confirm holds into a booking |
| My bookings | `/bookings` | Booking history and ticket retrieval |
| Admin panel | `/admin` | Manage movies, halls, showings |
| Login / Register | `/login`, `/register` | Authentication forms |

---

## 15. Deployment

The production app is deployed on **Render** (backend + frontend) with **Upstash Redis** as the managed Redis service.

### Services on Render

| Service | Type | Branch |
|---|---|---|
| `cinema-api` | Web Service (Docker) | `deploy` |
| `cinema-frontend` | Static Site | `deploy` |
| `cinema-db` | PostgreSQL (managed) | — |

### Deployment configuration (`render.yaml`)

The `render.yaml` file at the project root defines all services declaratively, enabling one-click deploys.

### CI pipeline (GitHub Actions)

On every push to any branch:
1. **Lint** — Python (flake8/ruff) + JavaScript (ESLint)
2. **Import smoke test** — `python -c "from app.main import app"` confirms the app loads
3. **Docker build** — builds the production image
4. **Frontend build** — `npm run build` confirms no TypeScript/JS errors

### Production environment variables (Render)

Set these in the Render dashboard:
```
APP_ENV=prod
SECRET_KEY=<strong-random-key-min-32-chars>
DATABASE_URL=<render-postgres-connection-string>
REDIS_URL=<upstash-redis-url>
CORS_ORIGINS=https://cinema-frontend-11qu.onrender.com
```

### Live URLs

| Service | URL |
|---|---|
| Frontend | https://cinema-frontend-11qu.onrender.com |
| API | https://cinema-api-5mey.onrender.com |
| Swagger Docs | https://cinema-api-5mey.onrender.com/docs |

---

## 16. Key Design Decisions

### Decision 1 — Redis SET NX EX for seat holds

**Problem:** Two users clicking the same seat simultaneously would both see it as `available` and both try to book it.

**Decision:** Use Redis `SET NX EX` (set if Not eXists, with EXpiry) as a 5-minute distributed lock per seat. The operation is atomic at the Redis level.

**Why Redis over DB:** A database-level pessimistic lock would hold a transaction open for up to 5 minutes, killing connection pool capacity under load. Redis locks are lightweight, auto-expire without a cleanup job, and release the DB immediately.

**Why DB constraint too:** Redis can fail or be restarted. The `UNIQUE(showing_id, seat_id)` constraint on `booking_seats` is the definitive guard — it makes double booking **physically impossible** at the database level.

---

### Decision 2 — Price computed at query time, frozen at booking time

**Problem:** If a price is stored when the showing is created, it doesn't react to demand. If it's computed every time but not frozen, a user could see $57.50 on the seat map but be charged $62.50 at confirmation.

**Decision:** Compute the price live on every `GET /showings/{id}/seats` request using current occupancy. When `POST /bookings` is called, compute the price **one final time** using current occupancy and freeze it into `price_at_booking`.

**Guarantee:** The price a user sees on the seat map is always what they pay, as long as they confirm within their 5-minute hold window (occupancy changes during that window are possible but minimal).

---

### Decision 3 — Soft delete for movies (`is_active = false`)

**Problem:** Deleting a movie row would orphan or cascade-delete its showings and booking history.

**Decision:** `DELETE /movies/{id}` sets `is_active = false`. The movie vanishes from customer-facing listings but all historical data is preserved for bookings, tickets, and admin queries.

---

### Decision 4 — Ticket codes instead of PDFs

**Problem:** Generating and storing PDF files requires significant infrastructure (storage, CDN) and adds complexity.

**Decision:** Each booking gets a short, unique, URL-safe ticket code (e.g., `TKT-7G2K-9XW1`) using `secrets.choice` with an unambiguous alphabet (no `0`/`O`, `1`/`I`). The code itself is the `qr_payload` — any QR scanner can read it. PDF generation can be added later as a wrapper around this code.

---

### Decision 5 — Separate `booking_seats` join table with redundant `showing_id`

**Problem:** To check if a seat is booked for a specific showing, you'd normally join `booking_seats → bookings → showing_id`. This is an extra join on the hot path (every seat map request).

**Decision:** Add `showing_id` directly to `booking_seats` as a denormalized column with its own index. The unique constraint `UNIQUE(showing_id, seat_id)` then lives on this table directly — making the double-booking check a single indexed lookup with no joins.

---

### Decision 6 — All-or-nothing hold acquisition

**Problem:** If a user selects 4 seats and seat 3 is taken, what happens to the other 3 holds?

**Decision:** If **any** seat in a hold request is unavailable, **all** acquired holds for that request are immediately rolled back. The API returns `409` with the specific conflicting seat IDs. This prevents users from accidentally holding partial seat groups that they can't complete.

---

*Documentation generated: June 2026*
