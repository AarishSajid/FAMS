"""
Redis client and sorted-set helpers for the service request queue.

Queue strategy (from spec Section 11):
  ZADD fams:requests:<service_center_id> <unix_timestamp> <request_id>
  - Score = unix timestamp of requestedAt → oldest first via ZRANGE.
  - ZREM on completion/decline.
"""

import random
import redis
from config import get_settings

settings = get_settings()

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def _queue_key(service_center_id: int) -> str:
    return f"fams:requests:{service_center_id}"


def _leaderboard_key(cache_key: str) -> str:
    return f"fams:leaderboard:{cache_key}"


# ── Single-flight lock (cache-stampede guard) ────────────────

def acquire_lock(name: str, ttl: int = 30) -> bool:
    """Try to grab a short-lived recompute lock. True = caller should recompute.
    # ponytail: one global per-key lock; fine for low-write caches. Upgrade to
    # a fenced/Redlock token only if multi-node recompute correctness matters."""
    return bool(redis_client.set(f"fams:lock:{name}", "1", nx=True, ex=ttl))


def release_lock(name: str):
    redis_client.delete(f"fams:lock:{name}")


# ── Service Request Queue (Sorted Sets) ──────────────────────

def enqueue_request(service_center_id: int, request_id: int, timestamp: float):
    """Add a new service request to the queue (oldest-first ordering)."""
    redis_client.zadd(_queue_key(service_center_id), {str(request_id): timestamp})


def dequeue_request(service_center_id: int, request_id: int):
    """Remove a completed/declined request from the queue."""
    redis_client.zrem(_queue_key(service_center_id), str(request_id))


def get_request_queue(service_center_id: int, start: int = 0, end: int = -1) -> list[str]:
    """Get request IDs in chronological order (oldest → newest)."""
    return redis_client.zrange(_queue_key(service_center_id), start, end)


# ── Leaderboard Cache ────────────────────────────────────────

def get_cached_leaderboard(cache_key: str) -> str | None:
    """Get cached leaderboard JSON, or None if expired/missing."""
    return redis_client.get(_leaderboard_key(cache_key))


def set_cached_leaderboard(cache_key: str, data: str, ttl: int = 3600):
    """Cache leaderboard JSON for ~1 hour, with jitter so keys created together
    don't all expire at the same instant (desynchronizes the herd)."""
    redis_client.set(_leaderboard_key(cache_key), data, ex=ttl + random.randint(0, 300))


def invalidate_leaderboard_center(service_center_id: int | None):
    """Clear every cached window for a center (keys `<id>:<window>`) plus the
    global aggregate (id 0). Called after any change that shifts agent standings."""
    ids = {"0", str(service_center_id)} if service_center_id else {"0"}
    for _id in ids:
        keys = list(redis_client.scan_iter(match=f"fams:leaderboard:{_id}:*"))
        if keys:
            redis_client.delete(*keys)
