"""
Seed script – creates all DB tables then inserts:
  - 1 admin user   (admin@cinema.com / admin1234)
  - 30 movies
  - 4 halls        (A 10×10 VIP last row, B 8×12, C 12×15 IMAX VIP last 2 rows, D 6×8 cozy)
  - ~150 showings spread over the next 21 days across all halls
  All prices are in USD ($).

Run inside the API container:
    docker compose exec api python seed.py
"""

import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.database import engine, AsyncSessionLocal, Base
from app.models import User, Movie, Hall, Seat, Showing
from app.security import hash_password


def _row_label(i: int) -> str:
    return chr(ord("A") + i)


# TMDB CDN base — stable image host for real commercial movie posters.
TMDB = "https://image.tmdb.org/t/p/w500"


# ─────────────────────────── MOVIES ────────────────────────────────────────
# Each movie uses the official poster of its real-world franchise entry.

MOVIES_DATA = [
    # ── Big franchise movies (use the real official posters) ────────────
    {"title": "Dune: Part Three",                    "description": "The Fremen rise as Paul Atreides faces his ultimate destiny on the desert planet Arrakis.",                            "duration_minutes": 165, "genre": "Sci-Fi",     "rating": "PG-13", "poster_url": f"{TMDB}/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg"},  # Dune: Part Two
    {"title": "The Grand Heist",                     "description": "A legendary crew of thieves plans the most audacious robbery in Monaco's history.",                                    "duration_minutes": 128, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/hQQCdZrsHtZyR6NbKH2YyCqd2fR.jpg"},  # Ocean's Eleven
    {"title": "Quiet River",                         "description": "A meditative drama about family, forgiveness, and the slow passage of time in rural Montana.",                         "duration_minutes": 112, "genre": "Drama",      "rating": "PG",    "poster_url": f"{TMDB}/oikfdSiM50Iib2cTcrlrEDOXkQy.jpg"},  # Nomadland
    {"title": "Avengers: Secret Wars",               "description": "The greatest heroes of every reality unite to stop an incursion threatening the entire multiverse.",                   "duration_minutes": 180, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/or06FN3Dka5tukK1e9sl16pB3iy.jpg"},  # Avengers: Endgame
    {"title": "Spider-Man: Beyond the Spider-Verse", "description": "Miles Morales leaps across dimensions once more to make the ultimate sacrifice that could save every universe.",       "duration_minutes": 145, "genre": "Animation",  "rating": "PG",    "poster_url": f"{TMDB}/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg"},  # Spider-Man: Across the Spider-Verse
    {"title": "Mission: Impossible – Final Reckoning","description": "Ethan Hunt faces his most impossible mission yet: stopping a rogue AI controlling every weapon on Earth.",            "duration_minutes": 163, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/z53D0aTc65bKQZ8PdJiSLMjDKUt.jpg"},  # Mission: Impossible – Dead Reckoning
    {"title": "The Dark Knight Returns",             "description": "An older Bruce Wayne returns to the cape when a new villain threatens to tear Gotham apart.",                          "duration_minutes": 155, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/qJ2tW6WMUDux911r6m7haRef0WH.jpg"},  # The Dark Knight
    {"title": "Jurassic World: Rebirth",             "description": "Five years after BioSyn's fall, a covert team ventures into the wildest corners of Earth to collect ancient DNA.",     "duration_minutes": 140, "genre": "Adventure",  "rating": "PG-13", "poster_url": f"{TMDB}/wWqVO7gUUe7g3LhdLcUTphzITWp.jpg"},  # Jurassic World: Dominion
    {"title": "Avatar: Fire and Ash",                "description": "Jake Sully and Neytiri lead the Na'vi against a volcanic catastrophe as a terrifying new enemy rises from Pandora.",   "duration_minutes": 170, "genre": "Sci-Fi",     "rating": "PG-13", "poster_url": f"{TMDB}/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"},  # Avatar: The Way of Water
    {"title": "John Wick: Chapter 5",                "description": "Declared excommunicado from every guild, John Wick wages a one-man war against the global assassin network.",         "duration_minutes": 130, "genre": "Action",     "rating": "R",     "poster_url": f"{TMDB}/vZloFAK7NmvMGKE7VkF5UHaz0I.jpg"},  # John Wick: Chapter 4
    {"title": "Top Gun: Maverick 2",                 "description": "Maverick is back in the cockpit to train a new generation of pilots for a mission no one has attempted before.",      "duration_minutes": 135, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/62HCnUTCjDVGbCbBGiGMDJBklHV.jpg"},  # Top Gun: Maverick
    {"title": "Interstellar 2",                      "description": "A new crew travels beyond known space to find what Cooper left behind — and discovers the secret to save humanity.",  "duration_minutes": 175, "genre": "Sci-Fi",     "rating": "PG-13", "poster_url": f"{TMDB}/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg"},  # Interstellar
    {"title": "The Batman Part II",                  "description": "Batman investigates a new wave of terror in Gotham while confronting an enemy who knows his true identity.",          "duration_minutes": 158, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/74xTEgt7R36Fpooo50r9T25onhq.jpg"},  # The Batman
    {"title": "Guardians of the Galaxy Vol. 4",      "description": "The Guardians reunite for one final mission at the edge of the cosmos — and are forced to say goodbye forever.",      "duration_minutes": 142, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/r2J02Z2OpNTctfOSN1Ydgii51I3.jpg"},  # Guardians of the Galaxy Vol. 3
    {"title": "Deadpool & Wolverine 2",              "description": "The Merc with a Mouth and Wolverine are back — twice the chaos, twice the carnage, zero dignity.",                    "duration_minutes": 127, "genre": "Action",     "rating": "R",     "poster_url": f"{TMDB}/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg"},  # Deadpool & Wolverine
    {"title": "Inside Out 3",                        "description": "Riley faces the challenges of young adulthood as her emotions evolve — and two powerful new feelings appear.",        "duration_minutes": 105, "genre": "Animation",  "rating": "G",     "poster_url": f"{TMDB}/vpnVM9B6NMmQpWeZvzLvDESb2QY.jpg"},  # Inside Out 2
    {"title": "Oppenheimer: Trinity",                "description": "The untold story after the bomb — the guilt, the legacy, and the political battles that defined the Cold War.",      "duration_minutes": 178, "genre": "Drama",      "rating": "R",     "poster_url": f"{TMDB}/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg"},  # Oppenheimer
    {"title": "Fast X: Part 2",                      "description": "Dom Toretto races across three continents to save his family from the most ruthless enemy they have ever faced.",     "duration_minutes": 145, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/1E5baAaEse26fej7uHcjOgEE2t2.jpg"},  # Fast X
    {"title": "Moana 3",                             "description": "Moana sails beyond the known ocean to discover lost civilisations and ancient powers that challenge her beliefs.",     "duration_minutes": 110, "genre": "Animation",  "rating": "G",     "poster_url": f"{TMDB}/4YZpsylmjHbqeWzjKpUEF8gcLNW.jpg"},  # Moana 2
    {"title": "Inception: Reawakened",               "description": "A new team of dream thieves descends deeper than anyone has ever dared — into a subconscious with no escape.",         "duration_minutes": 168, "genre": "Sci-Fi",     "rating": "PG-13", "poster_url": f"{TMDB}/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg"},  # Inception

    # ── New original titles (real posters from same-genre films) ────────
    {"title": "The Northern Lights",                 "description": "A reclusive astronomer in remote Iceland discovers a celestial event that could rewrite the laws of physics.",         "duration_minutes": 122, "genre": "Drama",      "rating": "PG-13", "poster_url": f"{TMDB}/4nt77YkLLrRMSjFnNTplJI2BjB.jpg"},  # The Lighthouse
    {"title": "Phantom Protocol",                    "description": "A disavowed CIA operative uncovers a conspiracy that reaches the highest levels of every government.",                 "duration_minutes": 138, "genre": "Thriller",   "rating": "R",     "poster_url": f"{TMDB}/3qpUWfwHGNTfXLrJjPPnX02FE3l.jpg"},  # Mission: Impossible Ghost Protocol
    {"title": "Echoes of Tomorrow",                  "description": "A scientist receives messages from her future self warning of a catastrophe only she can prevent.",                    "duration_minutes": 130, "genre": "Sci-Fi",     "rating": "PG-13", "poster_url": f"{TMDB}/yIZ1xendyqKvY0V0qbBduI7WIvL.jpg"},  # Arrival
    {"title": "The Last Kingdom",                    "description": "A young queen must reclaim her stolen throne and unite warring clans before her kingdom falls forever.",               "duration_minutes": 150, "genre": "Fantasy",    "rating": "PG-13", "poster_url": f"{TMDB}/wF6SsBF5tlVeWiKvE2qcM85ZIQI.jpg"},  # The Woman King
    {"title": "Midnight in Tokyo",                   "description": "A love story unfolds over a single night through the neon-lit streets of Shibuya.",                                    "duration_minutes": 108, "genre": "Romance",    "rating": "PG-13", "poster_url": f"{TMDB}/8wRoyo7VFAxcSzCnvVoGNFlIIzz.jpg"},  # Lost in Translation
    {"title": "The Cartel Wars",                     "description": "An undercover DEA agent walks the razor's edge between justice and survival inside the world's most violent cartel.", "duration_minutes": 144, "genre": "Crime",      "rating": "R",     "poster_url": f"{TMDB}/peNjwx8U9iYpLpd5T0KFCEFTLEX.jpg"},  # Sicario
    {"title": "Sky Pirates",                         "description": "In a steampunk world of floating cities, a band of misfits hijacks an airship to save their dying homeland.",          "duration_minutes": 118, "genre": "Adventure",  "rating": "PG",    "poster_url": f"{TMDB}/zGGRO5dcDjlj7DvbDdgwoKVgrIv.jpg"},  # Treasure Planet
    {"title": "The Whispering Woods",                "description": "Four childhood friends return to the cabin where, twenty years ago, one of them disappeared without a trace.",         "duration_minutes": 115, "genre": "Horror",     "rating": "R",     "poster_url": f"{TMDB}/2uNW4WbgBXL25BAbXGLnLqX71Sw.jpg"},  # Hereditary
    {"title": "Champions Rise",                      "description": "An underdog Olympic gymnastics team faces impossible odds in their quest for gold against unbeatable rivals.",          "duration_minutes": 124, "genre": "Sports",     "rating": "PG",    "poster_url": f"{TMDB}/pCofRSL3pHFLDP2dxpLnueDxxQI.jpg"},  # Rocky
    {"title": "The Final Equation",                  "description": "A brilliant mathematics professor races against time to solve a 200-year-old problem before her rival does.",          "duration_minutes": 119, "genre": "Drama",      "rating": "PG-13", "poster_url": f"{TMDB}/zBzclR5SNgwQ9OFGCV3y5j6cAQc.jpg"},  # Hidden Figures

    # ── Poster-first additions ──────────────────────────────────────────
    # Famous real movies — the poster IS the marketing here, so descriptions
    # stay short and the genre/rating come straight from the original film.
    {"title": "Joker",                               "description": "A failed comedian descends into madness in Gotham City.",                       "duration_minutes": 122, "genre": "Drama",      "rating": "R",     "poster_url": f"{TMDB}/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg"},
    {"title": "Inception",                           "description": "A thief who steals secrets through dream-sharing technology.",                  "duration_minutes": 148, "genre": "Sci-Fi",     "rating": "PG-13", "poster_url": f"{TMDB}/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg"},
    {"title": "Pulp Fiction",                        "description": "The lives of two mob hitmen, a boxer, and a gangster's wife intertwine.",       "duration_minutes": 154, "genre": "Crime",      "rating": "R",     "poster_url": f"{TMDB}/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg"},
    {"title": "The Godfather",                       "description": "The aging patriarch of an organized crime dynasty transfers control.",          "duration_minutes": 175, "genre": "Crime",      "rating": "R",     "poster_url": f"{TMDB}/3bhkrj58Vtu7enYsRolD1fZdja1.jpg"},
    {"title": "Forrest Gump",                        "description": "A simple man witnesses and influences several defining historical events.",     "duration_minutes": 142, "genre": "Drama",      "rating": "PG-13", "poster_url": f"{TMDB}/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg"},
    {"title": "The Matrix",                          "description": "A hacker learns the shocking truth about his reality.",                         "duration_minutes": 136, "genre": "Sci-Fi",     "rating": "R",     "poster_url": f"{TMDB}/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg"},
    {"title": "Gladiator",                           "description": "A betrayed Roman general rises through the ranks of the gladiatorial arena.",   "duration_minutes": 155, "genre": "Action",     "rating": "R",     "poster_url": f"{TMDB}/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg"},
    {"title": "Parasite",                            "description": "Greed and class discrimination threaten a newly formed symbiotic relationship.","duration_minutes": 132, "genre": "Thriller",   "rating": "R",     "poster_url": f"{TMDB}/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg"},
    {"title": "The Lion King",                       "description": "A young lion prince flees his kingdom after the murder of his father.",         "duration_minutes": 88,  "genre": "Animation",  "rating": "G",     "poster_url": f"{TMDB}/sKCr78MXSLixwmZ8DyJLrpMsd15.jpg"},
    {"title": "Titanic",                             "description": "A seventeen-year-old aristocrat falls in love with a poor artist aboard RMS Titanic.","duration_minutes": 195, "genre": "Romance",  "rating": "PG-13", "poster_url": f"{TMDB}/9xjZS2rlVxm8SFx8kPC3aIGCOYQ.jpg"},
    {"title": "The Shawshank Redemption",            "description": "Two imprisoned men bond over years, finding solace and redemption.",            "duration_minutes": 142, "genre": "Drama",      "rating": "R",     "poster_url": f"{TMDB}/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg"},
    {"title": "Fight Club",                          "description": "An insomniac office worker and a soap salesman form an underground club.",      "duration_minutes": 139, "genre": "Drama",      "rating": "R",     "poster_url": f"{TMDB}/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"},
    {"title": "Frozen",                              "description": "A fearless princess sets off on a journey to find her estranged sister.",       "duration_minutes": 102, "genre": "Animation",  "rating": "PG",    "poster_url": f"{TMDB}/kgwjIb2JDHRhNk13lmSxiClFjVk.jpg"},
    {"title": "Black Panther",                       "description": "T'Challa returns home to Wakanda to take his rightful place as king.",          "duration_minutes": 134, "genre": "Action",     "rating": "PG-13", "poster_url": f"{TMDB}/uxzzxijgPIY7slzFvMotPv8wjKA.jpg"},
    {"title": "Coco",                                "description": "A young boy is accidentally transported to the Land of the Dead.",              "duration_minutes": 105, "genre": "Animation",  "rating": "PG",    "poster_url": f"{TMDB}/gGEsBPAijhVUFoiNpgZXqRVWJt2.jpg"},
]


# ─────────────────────── HALL CONFIGURATION ────────────────────────────────
#
#  Hall A  – 10 × 10  (standard, last row J = VIP)
#  Hall B  –  8 × 12  (standard, all standard)
#  Hall C  – 12 × 15  (IMAX, rows K & L = VIP)
#  Hall D  –  6 ×  8  (cozy small screen)

HALL_SLOTS = [
    [(10, 0),  (13, 30), (17, 0),  (20, 30)],   # Hall A
    [(10, 30), (14, 0),  (17, 30), (21, 0)],    # Hall B
    [(11, 0),  (14, 30), (18, 0),  (21, 30)],   # Hall C
    [(11, 30), (15, 0),  (18, 30)],             # Hall D
]

HALL_PRICES = [
    ["13.00", "13.00", "15.00", "16.00"],   # Hall A
    ["11.00", "12.00", "13.00", "14.00"],   # Hall B
    ["20.00", "20.00", "22.00", "22.00"],   # Hall C — IMAX premium
    ["10.00", "10.00", "11.00"],            # Hall D
]


def generate_showings_plan(num_movies: int, days: int = 20, per_movie: int = 5):
    """Assign each movie ~`per_movie` non-conflicting (day, hall, slot) tuples."""
    rng = random.Random(42)              # deterministic
    used = set()
    plan = []
    for movie_idx in range(num_movies):
        added, attempts = 0, 0
        while added < per_movie and attempts < 200:
            day      = rng.randint(1, days)
            hall_idx = rng.randint(0, 3)
            slot_idx = rng.randint(0, len(HALL_SLOTS[hall_idx]) - 1)
            key = (day, hall_idx, slot_idx)
            if key not in used:
                used.add(key)
                plan.append((movie_idx, day, hall_idx, slot_idx))
                added += 1
            attempts += 1
    return plan


async def seed():
    # ── 1. Tables ────────────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:

        # ── 2. Admin ─────────────────────────────────────────────────────
        if not (await db.execute(select(User).where(User.email == "admin@cinema.com"))).scalar_one_or_none():
            db.add(User(
                email="admin@cinema.com",
                password_hash=hash_password("admin1234"),
                full_name="Cinema Admin",
                role="admin",
            ))

        # ── 3. Movies ────────────────────────────────────────────────────
        existing = (await db.execute(select(Movie))).scalars().first()
        if not existing:
            for m in MOVIES_DATA:
                db.add(Movie(**m))
            await db.flush()
        movies = (await db.execute(select(Movie).order_by(Movie.id))).scalars().all()

        # ── 4. Halls ─────────────────────────────────────────────────────
        async def get_or_create_hall(name, rows, cols, vip_rows):
            hall = (await db.execute(select(Hall).where(Hall.name == name))).scalar_one_or_none()
            if not hall:
                hall = Hall(name=name, rows_count=rows, cols_count=cols)
                db.add(hall)
                await db.flush()
                for r in range(rows):
                    for c in range(cols):
                        stype = "vip" if r >= (rows - vip_rows) else "standard"
                        db.add(Seat(hall_id=hall.id, row_label=_row_label(r), seat_number=c + 1, seat_type=stype))
            return hall

        halls = [
            await get_or_create_hall("Hall A", 10, 10, 1),
            await get_or_create_hall("Hall B",  8, 12, 0),
            await get_or_create_hall("Hall C", 12, 15, 2),
            await get_or_create_hall("Hall D",  6,  8, 0),
        ]
        await db.flush()

        # ── 5. Showings ──────────────────────────────────────────────────
        existing_showing = (await db.execute(select(Showing))).scalars().first()
        if not existing_showing:
            plan = generate_showings_plan(num_movies=len(movies), days=20, per_movie=5)
            now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            for movie_idx, day_offset, hall_idx, slot_idx in plan:
                h, m = HALL_SLOTS[hall_idx][slot_idx]
                db.add(Showing(
                    movie_id   = movies[movie_idx].id,
                    hall_id    = halls[hall_idx].id,
                    start_time = now + timedelta(days=day_offset, hours=h, minutes=m),
                    base_price = Decimal(HALL_PRICES[hall_idx][slot_idx]),
                ))
            total_showings = len(plan)
        else:
            total_showings = (await db.execute(select(Showing))).scalars().all()
            total_showings = len(total_showings)

        await db.commit()

        print("✅ Seed complete.")
        print(f"   Admin     : admin@cinema.com / admin1234")
        print(f"   Movies    : {len(MOVIES_DATA)}")
        print(f"   Halls     : 4  (A 10×10, B 8×12, C 12×15 IMAX, D 6×8)")
        print(f"   Showings  : {total_showings}  (spread over 20 days, USD pricing)")


if __name__ == "__main__":
    asyncio.run(seed())
