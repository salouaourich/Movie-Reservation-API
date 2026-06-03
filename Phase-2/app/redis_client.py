"""
Single shared async Redis client. We use redis-py's asyncio interface
(aioredis is now part of redis>=4.2 — same API, just `redis.asyncio`).
"""

import redis.asyncio as redis_asyncio

from app.config import REDIS_URL

# decode_responses=True so we get str back instead of bytes.
redis_client = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
