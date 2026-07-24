"""
Delta Sync Service — fetches changes from the Agriverse REST API and pushes
them through RabbitMQ into the local FAMS database.

Flow:
  1. Authenticate with the Agriverse API → get Bearer token.
  2. For each syncable entity (users, farms, field crops, services, products, etc.):
     a. Read the high-water mark (last seen updatedAt) from Redis.
     b. Call the appropriate Agriverse API endpoint.
     c. Filter records where updatedAt > highWaterMark.
     d. Push changed records to RabbitMQ (sync_updates_queue).
     e. Update the Redis high-water mark to max(updatedAt).
  3. The worker process consumes from the queue and upserts into the local DB.
"""

import logging
from datetime import datetime, timezone

import httpx

from config import get_settings
from redis_client import get_sync_hwm, set_sync_hwm, redis_client
from services.rabbitmq_service import publish_sync_updates

logger = logging.getLogger("fams.sync")
settings = get_settings()

# Token cache key in Redis
_TOKEN_KEY = "fams:sync:agriverse_token"


def _get_client() -> httpx.Client:
    """Create an httpx client with SSL settings."""
    return httpx.Client(
        base_url=settings.AGRIVERSE_API_URL,
        verify=settings.AGRIVERSE_VERIFY_SSL,
        timeout=30.0,
    )


def _authenticate(client: httpx.Client) -> str | None:
    """Authenticate against the Agriverse API and return a Bearer token.
    Caches the token in Redis for reuse across sync runs."""
    # Check Redis cache first
    cached = redis_client.get(_TOKEN_KEY)
    if cached:
        # Verify it's still valid with a quick /auth/me call
        try:
            r = client.get("/auth/me", headers={"Authorization": f"Bearer {cached}"})
            if r.status_code == 200:
                return cached
        except Exception:
            pass

    # Need a fresh token
    if not settings.AGRIVERSE_SYNC_EMAIL or not settings.AGRIVERSE_SYNC_PASSWORD:
        logger.warning("AGRIVERSE_SYNC_EMAIL / AGRIVERSE_SYNC_PASSWORD not set. Sync cannot authenticate.")
        return None

    try:
        r = client.post("/auth/login", json={
            "email": settings.AGRIVERSE_SYNC_EMAIL,
            "password": settings.AGRIVERSE_SYNC_PASSWORD,
        })
        r.raise_for_status()
        data = r.json()
        token = data.get("accessToken")
        if token:
            # Cache for 50 minutes (tokens expire in 60)
            redis_client.set(_TOKEN_KEY, token, ex=3000)
            logger.info("Authenticated with Agriverse API successfully.")
            return token
    except Exception as e:
        logger.error(f"Failed to authenticate with Agriverse API: {e}")

    return None


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _filter_changed(records: list[dict], hwm: str | None, timestamp_key: str = "updatedAt") -> list[dict]:
    """Filter records whose updatedAt is newer than the high-water mark."""
    if not hwm:
        # First sync ever — everything is new
        return records

    changed = []
    for rec in records:
        rec_ts = rec.get(timestamp_key)
        if rec_ts and rec_ts > hwm:
            changed.append(rec)
    return changed


def _max_timestamp(records: list[dict], timestamp_key: str = "updatedAt") -> str | None:
    """Return the maximum updatedAt from a list of records."""
    timestamps = [r.get(timestamp_key) for r in records if r.get(timestamp_key)]
    return max(timestamps) if timestamps else None


# ── Per-Entity Sync Functions ────────────────────────────────────


def _sync_service_centers(client: httpx.Client, token: str) -> int:
    """Sync ServiceCenter table."""
    entity = "service_centers"
    hwm = get_sync_hwm(entity)

    try:
        r = client.get("/service-center", headers=_auth_headers(token))
        r.raise_for_status()
        all_records = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch service centers: {e}")
        return 0

    changed = _filter_changed(all_records, hwm)
    if not changed:
        return 0

    updates = [{"entity": "service_center", "data": rec} for rec in changed]
    publish_sync_updates(updates)

    new_hwm = _max_timestamp(changed)
    if new_hwm:
        set_sync_hwm(entity, new_hwm)

    return len(changed)


def _sync_users(client: httpx.Client, token: str) -> int:
    """Sync User table (field agents + managers from all service centers)."""
    entity = "users"
    hwm = get_sync_hwm(entity)

    try:
        r = client.get("/users/field-agents", headers=_auth_headers(token))
        r.raise_for_status()
        all_records = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        return 0

    changed = _filter_changed(all_records, hwm)
    if not changed:
        return 0

    updates = [{"entity": "user", "data": rec} for rec in changed]
    publish_sync_updates(updates)

    new_hwm = _max_timestamp(changed)
    if new_hwm:
        set_sync_hwm(entity, new_hwm)

    return len(changed)


def _sync_farms(client: httpx.Client, token: str) -> int:
    """Sync Farm table — fetches farms from each service center."""
    entity = "farms"
    hwm = get_sync_hwm(entity)
    total_changed = 0

    # First get all service centers to iterate their farms
    try:
        r = client.get("/service-center", headers=_auth_headers(token))
        r.raise_for_status()
        centers = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch service centers for farm sync: {e}")
        return 0

    all_changed = []
    for center in centers:
        center_id = center.get("id")
        if not center_id:
            continue

        try:
            r = client.get(f"/service-center/{center_id}", headers=_auth_headers(token))
            r.raise_for_status()
            sc_data = r.json()
            farms = sc_data.get("farms", [])
        except Exception as e:
            logger.error(f"Failed to fetch farms for SC {center_id}: {e}")
            continue

        # Tag each farm with its serviceCenterId for upsert
        for farm in farms:
            farm["serviceCenterId"] = center_id

        changed = _filter_changed(farms, hwm)
        all_changed.extend(changed)

    if all_changed:
        updates = [{"entity": "farm", "data": rec} for rec in all_changed]
        publish_sync_updates(updates)
        total_changed = len(all_changed)

        new_hwm = _max_timestamp(all_changed)
        if new_hwm:
            set_sync_hwm(entity, new_hwm)

    return total_changed


def _sync_field_crops(client: httpx.Client, token: str, farm_ids: list[int]) -> int:
    """Sync FieldCrop table — fetches field crops per farm."""
    entity = "field_crops"
    hwm = get_sync_hwm(entity)
    all_changed = []

    for farm_id in farm_ids:
        try:
            r = client.get(f"/farm/{farm_id}/fields", headers=_auth_headers(token))
            r.raise_for_status()
            fields = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch fields for farm {farm_id}: {e}")
            continue

        for field in fields:
            for fc in field.get("fieldCrop", []):
                fc["farmId"] = farm_id
                fc_updated = fc.get("updatedAt")
                if not hwm or (fc_updated and fc_updated > hwm):
                    all_changed.append(fc)

    if all_changed:
        updates = [{"entity": "field_crop", "data": rec} for rec in all_changed]
        publish_sync_updates(updates)

        new_hwm = _max_timestamp(all_changed)
        if new_hwm:
            set_sync_hwm(entity, new_hwm)

    return len(all_changed)


def _sync_services(client: httpx.Client) -> int:
    """Sync Service catalogue (public, no auth needed)."""
    entity = "services"
    hwm = get_sync_hwm(entity)

    try:
        r = client.get("/service")
        r.raise_for_status()
        all_records = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch services: {e}")
        return 0

    changed = _filter_changed(all_records, hwm)
    if not changed:
        return 0

    updates = [{"entity": "service", "data": rec} for rec in changed]
    publish_sync_updates(updates)

    new_hwm = _max_timestamp(changed)
    if new_hwm:
        set_sync_hwm(entity, new_hwm)

    return len(changed)


def _sync_products(client: httpx.Client) -> int:
    """Sync Product catalogue (public, no auth needed)."""
    entity = "products"
    hwm = get_sync_hwm(entity)

    try:
        r = client.get("/product")
        r.raise_for_status()
        all_records = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch products: {e}")
        return 0

    changed = _filter_changed(all_records, hwm)
    if not changed:
        return 0

    updates = [{"entity": "product", "data": rec} for rec in changed]
    publish_sync_updates(updates)

    new_hwm = _max_timestamp(changed)
    if new_hwm:
        set_sync_hwm(entity, new_hwm)

    return len(changed)


def _sync_agrobot_advisories(client: httpx.Client, token: str, farm_ids: list[int]) -> int:
    """Sync FarmAdvisory (Agrobot raw output) for each farm."""
    entity = "farm_advisories"
    hwm = get_sync_hwm(entity)
    all_changed = []

    for farm_id in farm_ids:
        try:
            r = client.get(f"/agrobot/farm/{farm_id}", headers=_auth_headers(token))
            r.raise_for_status()
            advisories = r.json()
        except Exception as e:
            logger.error(f"Failed to fetch Agrobot advisories for farm {farm_id}: {e}")
            continue

        for adv in advisories:
            adv["farmId"] = farm_id
            adv_ts = adv.get("createdAt")  # FarmAdvisory uses createdAt
            if not hwm or (adv_ts and adv_ts > hwm):
                all_changed.append(adv)

    if all_changed:
        updates = [{"entity": "farm_advisory", "data": rec} for rec in all_changed]
        publish_sync_updates(updates)

        new_hwm = _max_timestamp(all_changed, timestamp_key="createdAt")
        if new_hwm:
            set_sync_hwm(entity, new_hwm)

    return len(all_changed)


# ── Main Entry Point ─────────────────────────────────────────────


def run_sync():
    """
    Main sync entry point — called by APScheduler every SYNC_INTERVAL_MINUTES.
    Authenticates, detects changes via updatedAt, pushes to RabbitMQ.
    """
    lock_key = "fams:sync:run_lock"
    
    # Try to acquire a lock for 10 minutes. If another sync is running, abort.
    if not redis_client.set(lock_key, "running", nx=True, ex=600):
        logger.warning("Sync is already running. Skipping this trigger.")
        return

    logger.info(f"Starting Agriverse Delta Sync. Target: {settings.AGRIVERSE_API_URL}")
    start = datetime.now(timezone.utc)

    client = _get_client()
    try:
        # 1. Authenticate
        token = _authenticate(client)
        if not token:
            logger.warning("Sync aborted — could not authenticate with Agriverse API.")
            return

        # 2. Sync each entity type (order matters: centers before farms, farms before field crops)
        counts = {}

        counts["service_centers"] = _sync_service_centers(client, token)
        counts["users"] = _sync_users(client, token)
        counts["farms"] = _sync_farms(client, token)

        # Get farm IDs from local DB for per-farm syncs
        from database import SessionLocal
        from models.farm import Farm
        db = SessionLocal()
        try:
            farm_ids = [f.id for f in db.query(Farm.id).all()]
        finally:
            db.close()

        counts["field_crops"] = _sync_field_crops(client, token, farm_ids)
        counts["services"] = _sync_services(client)
        counts["products"] = _sync_products(client)
        counts["farm_advisories"] = _sync_agrobot_advisories(client, token, farm_ids)

        # 3. Log summary
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        total = sum(counts.values())
        summary = ", ".join(f"{v} {k}" for k, v in counts.items() if v > 0)
        if total == 0:
            logger.info(f"Delta Sync complete in {elapsed:.1f}s — no changes detected.")
        else:
            logger.info(f"Delta Sync complete in {elapsed:.1f}s — pushed {total} updates to RabbitMQ: {summary}")

    except Exception as e:
        logger.error(f"Delta Sync failed: {e}")
    finally:
        client.close()
        redis_client.delete(lock_key)
