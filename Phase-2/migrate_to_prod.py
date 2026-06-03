"""
migrate_to_prod.py
==================
Copies all movies from your local database to the live production API.

Usage (run from Phase-2 folder with docker running):
    python migrate_to_prod.py
"""

import subprocess
import json
import urllib.request
import urllib.error

LIVE_API   = "https://cinema-api-5mey.onrender.com/api/v1"
ADMIN_EMAIL    = "admin@cinema.com"
ADMIN_PASSWORD = "admin1234"

# ── 1. Read movies from local DB via docker ───────────────────────────────────
print("Reading movies from local database...")

sql = (
    "SELECT json_agg(row_to_json(m)) FROM ("
    "  SELECT title, description, duration_minutes, genre, rating, poster_url"
    "  FROM movies ORDER BY id"
    ") m;"
)

result = subprocess.run(
    ["docker", "compose", "exec", "-T", "db",
     "psql", "-U", "cinema_user", "-d", "cinema_db",
     "-t", "-c", sql],
    capture_output=True, text=True,
    cwd=r"C:\Users\User\OneDrive\Desktop\Movie-Reservation-API\Phase-2"
)

if result.returncode != 0:
    print("ERROR reading local DB:", result.stderr)
    exit(1)

raw = result.stdout.strip()
if not raw or raw == "NULL":
    print("No movies found in local database.")
    exit(0)

local_movies = json.loads(raw)
print(f"Found {len(local_movies)} movies locally.\n")

# ── 2. Log in to live API ─────────────────────────────────────────────────────
print("Logging in to live API...")

login_data = json.dumps({"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).encode()
req = urllib.request.Request(
    f"{LIVE_API}/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read())["access_token"]
    print("Login OK.\n")
except urllib.error.HTTPError as e:
    print("Login FAILED:", e.read().decode())
    exit(1)

# ── 3. Fetch movies already on live API ───────────────────────────────────────
req = urllib.request.Request(
    f"{LIVE_API}/movies?page_size=100",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(req) as resp:
    live_titles = {m["title"].lower() for m in json.loads(resp.read())["items"]}

print(f"Live API already has {len(live_titles)} movies.")
to_add = [m for m in local_movies if m["title"].lower() not in live_titles]
print(f"Movies to add: {len(to_add)}\n")

if not to_add:
    print("Nothing to do — all movies are already on the live site!")
    exit(0)

# ── 4. POST each missing movie ────────────────────────────────────────────────
ok = 0
fail = 0

for movie in to_add:
    # Clean up None values
    payload = {k: v for k, v in movie.items() if v is not None}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{LIVE_API}/movies",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            created = json.loads(resp.read())
            print(f"  ✓ [{created['id']:>3}] {created['title']}")
            ok += 1
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ✗ FAILED '{movie['title']}': {e.code} {body}")
        fail += 1

print(f"\nDone. {ok} added, {fail} failed.")
