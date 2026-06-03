# Phase 3 — Security

This document explains the four security additions Phase 3 layers on top of the
Phase 2 implementation: **JWT authentication**, **role-based access control**,
**Pydantic input validation**, and **rate limiting**. Each section is written so
that you can defend it during the oral.

---

## 1. JWT authentication

### Flow
1. `POST /api/v1/auth/register` creates a `customer` user (admins are seeded,
   never self-registered).
2. `POST /api/v1/auth/login` verifies the password (bcrypt, via `passlib`) and
   returns an `access_token`.
3. Every protected endpoint requires `Authorization: Bearer <token>`.

### Token claims (HS256)
| Claim | Purpose |
|-------|---------|
| `sub` | User id |
| `role` | `customer` or `admin` (used for RBAC) |
| `iss` | Issuer string — rejected if it doesn't match `JWT_ISSUER` |
| `aud` | Audience — rejected if it doesn't match `JWT_AUDIENCE` |
| `iat` | Issued-at timestamp |
| `exp` | Expiry (60 minutes by default) |
| `jti` | Random uuid — uniquely identifies the token, enables future blocklist |

### Hardening choices
- **`iss` / `aud` validation** stops a token issued for a different service
  from being accepted here.
- **Single error message on token failure** (`INVALID_TOKEN`) — we don't tell
  the attacker whether the signature, audience, or expiry was the problem.
- **`SECRET_KEY` is checked at boot**: if `APP_ENV=prod` and the key is
  empty/default/`< 32 chars`, the process exits with a clear error rather
  than silently issuing trivially-forgeable tokens.
- **bcrypt** for password hashing (work factor managed by passlib defaults) +
  a Pydantic policy: ≥ 8 chars, must include lower, upper, and a digit.

### Files
- `app/security.py` — issuance + verification
- `app/config.py` — `SECRET_KEY`, `JWT_ISSUER`, `JWT_AUDIENCE`

---

## 2. Role-Based Access Control (RBAC)

Two roles, enforced via FastAPI dependencies:

| Role | Can call |
|------|----------|
| `customer` | Browse movies/showings/seat map, create holds, create/cancel **their own** bookings, fetch **their own** tickets |
| `admin` | All of the above + create/update/delete movies, halls, showings; view **any** booking |

### Implementation
- `get_current_user` → resolves the bearer token to a `User` row, or 401.
- `require_admin` → 403 if the role isn't `admin`.
- `require_customer` → 403 if the role isn't `customer`.
- Owner-or-admin checks live inline in `bookings.py::_load_booking_or_403`
  so a customer cannot read someone else's booking even by guessing the id.

### 401 vs 403 split
- **401 UNAUTHENTICATED / INVALID_TOKEN** — caller is not (validly) logged in
- **403 FORBIDDEN** — caller is logged in but lacks the role / ownership

---

## 3. Pydantic input validation

Every request body uses a `StrictModel` base with:

```python
model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
```

`extra="forbid"` makes the API **reject unknown fields**. This blocks mass-
assignment attacks (e.g. a client trying `{"role": "admin"}` on `/register`
will get a 400 instead of silently being ignored).

### Per-field protection
| Field | Constraints |
|-------|-------------|
| `email` | `EmailStr` (RFC-compliant) |
| `password` | 8–128 chars, must contain lower + upper + digit |
| `full_name` | 1–255 chars |
| `title`, `name`, `genre` | length-bounded |
| `description` | ≤ 4000 chars (anti-DoS) |
| `duration_minutes` | 1–600 (anti-DoS, sane upper bound) |
| `poster_url` | `^https?://.+`, ≤ 500 chars |
| `rating` | Enum (`G`, `PG`, `PG-13`, `R`, `NC-17`) |
| `seat_type`, `status`, `pricing_tier`, `role` | Enums |
| `rows_count`, `cols_count` | 1–50 |
| `seats` (HallCreate) | ≤ 2500 items |
| `row_label` | regex `^[A-Z]{1,3}$` |
| `base_price` | > 0, ≤ 9999.99, ≤ 2 decimals |
| `start_time` (Showing) | must be in the future |
| `seat_ids` (holds / bookings) | non-empty, ≤ 10 ids, positive, no duplicates |

The seat-id cap (`MAX_SEATS_PER_REQUEST = 10`) is a concrete anti-abuse
measure: without it, an attacker could submit `seat_ids = [1, …, 100_000]`
and force a giant SQL `IN` clause + Redis pipeline.

Validation failures are returned as the contract's standard envelope:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Request validation failed.", "details": { "errors": [ ... ] } } }
```

### Files
- `app/schemas.py`
- `app/main.py` — `validation_exception_handler`

---

## 4. Rate limiting

We use [`slowapi`](https://github.com/laurentS/slowapi). It plugs into FastAPI
as middleware and uses an in-memory store by default (Redis in prod via
`RATELIMIT_STORAGE_URI`).

### Identity (`key_func`)
- If a valid JWT is presented → rate-limit by `user:<sub>`
- Otherwise → rate-limit by `ip:<remote address>`

This stops the "register a fresh account per request" bypass — anonymous traffic
is constrained by IP even before the user exists.

### Default + per-route quotas

| Scope | Default | Why |
|-------|---------|-----|
| Global default | `120/minute` | Catches absent-minded scripts |
| `POST /auth/register` | `5/minute` | Stops mass account creation |
| `POST /auth/login` | `10/minute` | Stops credential-stuffing / brute force |
| `POST /showings/{id}/holds` | `30/minute` | Prevents hold-exhaustion DoS |
| `POST /bookings` | `20/minute` | Caps DB writes per actor |

When a quota is exceeded the response is:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{ "error": { "code": "RATE_LIMITED", "message": "Too many requests. ...", "details": { "limit": "10 per 1 minute" } } }
```

All quotas are environment-tunable (`RATE_LIMIT_LOGIN`, etc.) so they can be
relaxed in dev and tightened in prod without code changes.

### Files
- `app/rate_limit.py`
- `app/main.py` — middleware + 429 handler
- `app/routers/auth.py`
- `app/routers/showings.py`
- `app/routers/bookings.py`

---

## 5. Other defensive measures

- **CORS** is no longer `*` by default in prod — `CORS_ORIGINS` is a comma-
  separated allowlist read from env, and we restrict methods/headers.
- **Security headers** added via middleware: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`.
- **SQL injection** is prevented by SQLAlchemy's parameterized queries
  everywhere — no string interpolation into SQL.
- **Race-condition double-booking** is blocked by the
  `UniqueConstraint(showing_id, seat_id)` in `models.py` (the database is the
  final source of truth).
- **Seat holds** use `SET NX EX` in Redis (atomic acquire + TTL) so two
  concurrent holders cannot both win the same seat.

---

## 6. Threat model — short version

| Threat | Mitigation |
|--------|------------|
| Stolen token replay across services | `iss` + `aud` claims |
| Brute-force password guessing | bcrypt + login rate limit (10/min) |
| Mass-assignment of `role=admin` on register | Pydantic `extra="forbid"` + hard-coded `role="customer"` in the handler |
| Customer reading other customers' bookings | Owner-or-admin check in `_load_booking_or_403` |
| Race-condition double-booking | Redis hold + DB unique constraint |
| Payload DoS (huge seat list, huge description) | Field bounds + `MAX_SEATS_PER_REQUEST` |
| Credential stuffing across many IPs | Per-IP fallback in `key_func` + low login quota |
| SQL injection | SQLAlchemy parameterization |
| XSS in API responses | API returns JSON, no HTML render |
| Replay after logout | Out of scope this phase (would need a `jti` blocklist in Redis — the `jti` claim is already issued to make that one-line later) |
