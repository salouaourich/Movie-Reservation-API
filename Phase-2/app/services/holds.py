"""
Redis-based seat holds.

Key shape:   hold:showing:{showing_id}:seat:{seat_id}  -> value = user_id  (TTL = HOLD_TTL_SECONDS)

We use SET NX EX so only one user can hold a given seat at a time.
Acquisition is atomic across a list of seats: if any seat is already held,
none of the requested holds are kept (we roll back the ones we did acquire).
"""

from datetime import datetime, timedelta

from app.config import HOLD_TTL_SECONDS
from app.redis_client import redis_client


def _key(showing_id: int, seat_id: int) -> str:
    return f"hold:showing:{showing_id}:seat:{seat_id}"


async def get_hold_owner(showing_id: int, seat_id: int) -> str | None:
    """Return the user_id that currently holds this seat, or None."""
    return await redis_client.get(_key(showing_id, seat_id))


async def get_held_seat_ids(showing_id: int, seat_ids: list[int]) -> set[int]:
    """Return the subset of seat_ids that currently have an active hold (any user)."""
    if not seat_ids:
        return set()
    keys = [_key(showing_id, sid) for sid in seat_ids]
    values = await redis_client.mget(keys)
    return {sid for sid, val in zip(seat_ids, values) if val is not None}


async def acquire_holds(showing_id: int, seat_ids: list[int], user_id: int) -> tuple[bool, list[int], datetime]:
    """
    Try to acquire holds on every seat atomically.

    Returns (success, conflicts, expires_at):
      - success=True  -> all seats now held by this user, conflicts=[]
      - success=False -> none of the seats held; conflicts lists seat_ids that blocked us
    """
    acquired: list[int] = []
    conflicts: list[int] = []

    for sid in seat_ids:
        # SET key value NX EX ttl  -> returns True if set, None/False if key exists.
        ok = await redis_client.set(
            _key(showing_id, sid),
            str(user_id),
            nx=True,
            ex=HOLD_TTL_SECONDS,
        )
        if ok:
            acquired.append(sid)
        else:
            # Check if it's already this user's hold (refresh TTL) or someone else's.
            existing = await redis_client.get(_key(showing_id, sid))
            if existing == str(user_id):
                # Refresh TTL — caller already holds this seat.
                await redis_client.expire(_key(showing_id, sid), HOLD_TTL_SECONDS)
                acquired.append(sid)
            else:
                conflicts.append(sid)

    if conflicts:
        # Roll back any holds we just made so the operation is atomic from the user's POV.
        for sid in acquired:
            owner = await redis_client.get(_key(showing_id, sid))
            if owner == str(user_id):
                await redis_client.delete(_key(showing_id, sid))
        return False, conflicts, datetime.utcnow()

    expires_at = datetime.utcnow() + timedelta(seconds=HOLD_TTL_SECONDS)
    return True, [], expires_at


async def release_holds(showing_id: int, seat_ids: list[int], user_id: int) -> None:
    """Release holds owned by this user. Holds owned by others are left alone."""
    for sid in seat_ids:
        owner = await redis_client.get(_key(showing_id, sid))
        if owner == str(user_id):
            await redis_client.delete(_key(showing_id, sid))


async def release_all_user_holds(showing_id: int, user_id: int) -> None:
    """Scan all holds for this showing and remove those owned by this user."""
    pattern = f"hold:showing:{showing_id}:seat:*"
    async for key in redis_client.scan_iter(match=pattern):
        owner = await redis_client.get(key)
        if owner == str(user_id):
            await redis_client.delete(key)


async def user_owns_holds(showing_id: int, seat_ids: list[int], user_id: int) -> tuple[bool, list[int]]:
    """Confirm the user holds every seat in the list. Returns (ok, missing_seat_ids)."""
    missing: list[int] = []
    for sid in seat_ids:
        owner = await redis_client.get(_key(showing_id, sid))
        if owner != str(user_id):
            missing.append(sid)
    return (len(missing) == 0), missing


async def get_all_held_seats_for_showing(showing_id: int) -> set[int]:
    """Return every seat_id currently held (any user) for the showing — used by the seat map."""
    pattern = f"hold:showing:{showing_id}:seat:*"
    held: set[int] = set()
    async for key in redis_client.scan_iter(match=pattern):
        # key looks like 'hold:showing:42:seat:301'
        try:
            seat_id = int(key.rsplit(":", 1)[1])
            held.add(seat_id)
        except (ValueError, IndexError):
            continue
    return held
