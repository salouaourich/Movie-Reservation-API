# API Contract — Movie Reservation API

Base URL (local): `http://localhost:8000/api/v1`
Base URL (prod): `https://cinema-reservation-api.onrender.com/api/v1`

Auth: `Authorization: Bearer <jwt>` on protected routes. JWT carries `sub` (user id) and `role` (`customer` or `admin`).

All timestamps are ISO 8601 UTC. All money is `decimal` with 2 fractional digits, currency assumed AED.

---

## Quick map

| # | Method | Path | Auth | Role |
|---|--------|------|------|------|
| 1 | POST | `/auth/register` | public | — |
| 2 | POST | `/auth/login` | public | — |
| 3 | GET  | `/auth/me` | required | any |
| 4 | GET  | `/movies` | public | — |
| 5 | GET  | `/movies/{movie_id}` | public | — |
| 6 | POST | `/movies` | required | admin |
| 7 | PATCH | `/movies/{movie_id}` | required | admin |
| 8 | DELETE | `/movies/{movie_id}` | required | admin |
| 9 | GET  | `/movies/{movie_id}/showings` | public | — |
| 10 | POST | `/halls` | required | admin |
| 11 | GET  | `/halls` | required | admin |
| 12 | POST | `/showings` | required | admin |
| 13 | GET  | `/showings/{showing_id}` | public | — |
| 14 | GET  | `/showings/{showing_id}/seats` | public | — |
| 15 | POST | `/showings/{showing_id}/holds` | required | customer |
| 16 | DELETE | `/showings/{showing_id}/holds` | required | customer |
| 17 | POST | `/bookings` | required | customer |
| 18 | GET  | `/bookings/me` | required | customer |
| 19 | GET  | `/bookings/{booking_id}` | required | owner or admin |
| 20 | DELETE | `/bookings/{booking_id}` | required | owner or admin |
| 21 | GET  | `/bookings/{booking_id}/ticket` | required | owner or admin |

---

## 1. Auth

### POST `/auth/register`

Create a customer account. Admin accounts are seeded manually, not via this endpoint.

Request:
```json
{
  "email": "sal@example.com",
  "password": "min8chars",
  "full_name": "Sal Ouourich"
}
```
Response `201`:
```json
{
  "id": 7,
  "email": "sal@example.com",
  "full_name": "Sal Ouourich",
  "role": "customer",
  "created_at": "2026-05-12T10:00:00Z"
}
```
Errors: `400` validation, `409` email exists.

### POST `/auth/login`

Request:
```json
{ "email": "saloua@example.com", "password": "min8chars" }
```
Response `200`:
```json
{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
```
Errors: `401` invalid credentials.

### GET `/auth/me`

Response `200`:
```json
{ "id": 7, "email": "saloua@example.com", "full_name": "Sal Ouourich", "role": "customer" }
```
Errors: `401`.

---

## 2. Movies

### GET `/movies`

Query params: `?genre=action&search=dune&page=1&page_size=20`

Response `200`:
```json
{
  "items": [
    {
      "id": 1,
      "title": "Dune Part Three",
      "description": "...",
      "duration_minutes": 165,
      "genre": "sci-fi",
      "rating": "PG-13",
      "poster_url": "https://...",
      "is_active": true
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### GET `/movies/{movie_id}`

Response `200`: single movie object. Errors: `404`.

### POST `/movies` *(admin)*

Request:
```json
{
  "title": "Dune Part Three",
  "description": "...",
  "duration_minutes": 165,
  "genre": "sci-fi",
  "rating": "PG-13",
  "poster_url": "https://..."
}
```
Response `201`: movie object. Errors: `400`, `401`, `403`.

### PATCH `/movies/{movie_id}` *(admin)*

Partial update. Any subset of the POST fields plus `is_active`. Response `200`: movie object.

### DELETE `/movies/{movie_id}` *(admin)*

Soft delete (sets `is_active = false`). Response `204`. Errors: `404`, `409` if active showings exist.

### GET `/movies/{movie_id}/showings`

Query: `?date=2026-05-12`

Response `200`:
```json
{
  "items": [
    {
      "id": 42,
      "movie_id": 1,
      "hall_id": 3,
      "hall_name": "Hall A",
      "start_time": "2026-05-12T20:30:00Z",
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

## 3. Halls *(admin only)*

### POST `/halls`

Request:
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
If `seats` is omitted, the API auto-generates `rows_count × cols_count` standard seats. Response `201`: hall object with seat list. Errors: `400`, `401`, `403`.

### GET `/halls`

Response `200`: array of halls.

---

## 4. Showings

### POST `/showings` *(admin)*

Request:
```json
{
  "movie_id": 1,
  "hall_id": 3,
  "start_time": "2026-05-12T20:30:00Z",
  "base_price": "50.00"
}
```
Response `201`:
```json
{
  "id": 42,
  "movie_id": 1,
  "hall_id": 3,
  "start_time": "2026-05-12T20:30:00Z",
  "base_price": "50.00",
  "status": "scheduled"
}
```
Errors: `400`, `401`, `403`, `409` time overlap in the same hall.

### GET `/showings/{showing_id}`

Public. Response `200`: showing object with movie + hall expanded.

### GET `/showings/{showing_id}/seats` ← **the dynamic pricing endpoint**

Public.

Response `200`:
```json
{
  "showing_id": 42,
  "base_price": "50.00",
  "occupancy_rate": 0.62,
  "pricing_tier": "mid",
  "tier_multiplier": 1.15,
  "hall": { "id": 3, "name": "Hall A", "rows_count": 10, "cols_count": 10 },
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

`status` is one of `available`, `held` (a Redis hold exists), or `booked` (a confirmed booking row exists). `pricing_tier` is one of `low` (<50%), `mid` (50–80%), `high` (>80%).

Errors: `404`.

---

## 5. Seat Holds *(customer)*

### POST `/showings/{showing_id}/holds`

Acquire holds. Atomic across the list — if any one seat is unavailable, none are held.

Request:
```json
{ "seat_ids": [301, 304, 305] }
```
Response `201`:
```json
{
  "showing_id": 42,
  "held_seat_ids": [301, 304, 305],
  "expires_at": "2026-05-12T10:35:00Z",
  "ttl_seconds": 300
}
```
Errors:
- `400` empty list, malformed.
- `401` unauthenticated.
- `409` at least one seat already held or booked; response body lists the conflicting `seat_ids`.

### DELETE `/showings/{showing_id}/holds`

Release the user's own holds. Body: `{ "seat_ids": [301] }` (omit to release all of this user's holds for this showing). Response `204`.

---

## 6. Bookings *(customer)*

### POST `/bookings`

Convert holds into a confirmed booking. The caller must currently own holds on every seat in the list.

Request:
```json
{
  "showing_id": 42,
  "seat_ids": [301, 304, 305]
}
```
Response `201`:
```json
{
  "id": 88,
  "showing_id": 42,
  "user_id": 7,
  "status": "confirmed",
  "ticket_code": "TKT-7G2K-9XW1",
  "total_price": "172.50",
  "created_at": "2026-05-12T10:32:00Z",
  "seats": [
    { "seat_id": 301, "row_label": "A", "seat_number": 1, "price_at_booking": "57.50" },
    { "seat_id": 304, "row_label": "A", "seat_number": 4, "price_at_booking": "57.50" },
    { "seat_id": 305, "row_label": "A", "seat_number": 5, "price_at_booking": "57.50" }
  ]
}
```
Errors:
- `400` empty list.
- `401`.
- `409` user does not hold one or more seats / hold expired. Response body lists the failed seat_ids.

### GET `/bookings/me`

Response `200`:
```json
{
  "items": [
    {
      "id": 88,
      "showing_id": 42,
      "movie_title": "Dune Part Three",
      "hall_name": "Hall A",
      "start_time": "2026-05-12T20:30:00Z",
      "status": "confirmed",
      "total_price": "172.50",
      "ticket_code": "TKT-7G2K-9XW1",
      "created_at": "2026-05-12T10:32:00Z"
    }
  ]
}
```

### GET `/bookings/{booking_id}`

Caller must be the booking's owner or an admin. Response `200`: full booking object including seat detail. Errors: `403`, `404`.

### DELETE `/bookings/{booking_id}`

Cancel a booking. Sets `status = 'cancelled'`. Frees the seats for re-booking. Response `200`:
```json
{ "id": 88, "status": "cancelled", "cancelled_at": "2026-05-12T11:00:00Z" }
```
Errors: `403`, `404`, `409` showing already started.

### GET `/bookings/{booking_id}/ticket`

Response `200`:
```json
{
  "ticket_code": "TKT-7G2K-9XW1",
  "qr_payload": "TKT-7G2K-9XW1",
  "movie": { "title": "Dune Part Three", "duration_minutes": 165, "rating": "PG-13" },
  "showing": { "start_time": "2026-05-12T20:30:00Z", "hall_name": "Hall A" },
  "seats": [
    { "row_label": "A", "seat_number": 1, "seat_type": "standard" },
    { "row_label": "A", "seat_number": 4, "seat_type": "standard" },
    { "row_label": "A", "seat_number": 5, "seat_type": "standard" }
  ],
  "total_price": "172.50",
  "issued_at": "2026-05-12T10:32:00Z"
}
```
Errors: `403`, `404`, `409` if booking is cancelled.

---

## Error format

All error responses follow:
```json
{
  "error": {
    "code": "SEAT_UNAVAILABLE",
    "message": "Seats 301, 304 are already held by another user.",
    "details": { "seat_ids": [301, 304] }
  }
}
```

Status codes used:
- `400` validation error.
- `401` missing or invalid JWT.
- `403` authenticated but not authorized for this resource.
- `404` resource not found.
- `409` business-rule conflict (double booking, time overlap, hold expired, etc.).
- `429` rate limit exceeded.
- `500` unexpected server error.

---

## Rate limits (Phase 3)

Applied via `slowapi`:

- `/auth/login`: 5 requests per minute per IP.
- `/auth/register`: 3 requests per minute per IP.
- `/showings/{id}/holds` (POST): 10 requests per minute per user.
- All other endpoints: 60 requests per minute per IP.