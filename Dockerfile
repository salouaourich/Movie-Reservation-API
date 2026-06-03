# Root-level Dockerfile so Render (and any other container host that scans the
# repo root) can build the API without extra service-level path config.
#
# The actual application lives under Phase-2/. We mirror the Phase-2 Dockerfile
# here but with paths rewritten to the Phase-2/ subdirectory.

FROM python:3.11-slim

WORKDIR /app

# System dependencies needed by bcrypt / asyncpg / etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so subsequent code changes don't bust the layer cache.
COPY Phase-2/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Phase-2 backend (app/, seed.py, etc.) into the image root.
COPY Phase-2/ ./

EXPOSE 8000

# Production-style start: no --reload, single uvicorn worker.
# Render injects $PORT — fall back to 8000 for local docker builds.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
