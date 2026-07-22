"""
Redis client and sorted-set helpers for the service request queue.

Queue strategy (from spec Section 11):
  ZADD fams:requests:<service_center_id> <unix_timestamp> <request_id>
  - Score = unix timestamp of requestedAt → oldest first via ZRANGE.
  - ZREM on completion/decline.
"""

import redis
from config import get_settings

settings = get_settings()

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def _queue_key(service_center_id: int) -> str:
    return f"fams:requests:{service_center_id}"


def _leaderboard_key(service_center_id: int) -> str:
    return f"fams:leaderboard:{service_center_id}"


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

def get_cached_leaderboard(service_center_id: int) -> str | None:
    """Get cached leaderboard JSON, or None if expired/missing."""
    return redis_client.get(_leaderboard_key(service_center_id))


def set_cached_leaderboard(service_center_id: int, data: str, ttl: int = 3600):
    """Cache leaderboard JSON for 1 hour."""
    redis_client.set(_leaderboard_key(service_center_id), data, ex=ttl)


def invalidate_leaderboard(service_center_id: int):
    """Clear the leaderboard cache (e.g., after a case resolution)."""
    redis_client.delete(_leaderboard_key(service_center_id))


# ── Advisory Cache (optional) ────────────────────────────────

def get_cached_advisory(case_id: int) -> str | None:
    return redis_client.get(f"fams:advisory:{case_id}")


def set_cached_advisory(case_id: int, data: str, ttl: int = 300):
    redis_client.set(f"fams:advisory:{case_id}", data, ex=ttl)


def invalidate_advisory(case_id: int):
    redis_client.delete(f"fams:advisory:{case_id}")
