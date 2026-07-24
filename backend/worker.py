"""
RabbitMQ Consumer background worker.
Listens to two queues:
  1. 'advisories_queue' — processes new advisory cases from the cycle generator.
  2. 'sync_updates_queue' — upserts changed records from Agriverse delta sync.
"""

import json
import time
import pika
import logging
import traceback
from datetime import datetime, timezone
from config import get_settings
from database import SessionLocal
from models.advisory import AdvisoryCase, AdvisoryEvent
from models.user import User
from models.farm import Farm, FieldCrop, FarmAdvisory
from models.service_center import ServiceCenter, District
from models.service_request import Service, Product
from enums import AdvisoryCaseState, AdvisoryCaseKind, IssueType, AdvisorySeverity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fams.worker")

settings = get_settings()
ADVISORY_QUEUE = "advisories_queue"
SYNC_QUEUE = "sync_updates_queue"

def get_connection():
    parameters = pika.URLParameters(settings.RABBITMQ_URL)
    return pika.BlockingConnection(parameters)


# ── Advisory Queue Handler ───────────────────────────────────

def process_advisory(ch, method, properties, body):
    payload = json.loads(body)
    logger.info(f"Received advisory payload for farm {payload.get('farmId')}...")

    # Simulate heavy processing (the "doing its work" part requested by user)
    time.sleep(1.0) 

    db = SessionLocal()
    try:
        case = AdvisoryCase(
            cycleId=payload.get("cycleId"),
            farmId=payload.get("farmId"),
            fieldCropId=payload.get("fieldCropId"),
            sourceFarmAdvisoryId=payload.get("sourceFarmAdvisoryId"),
            serviceCenterId=payload.get("serviceCenterId"),
            kind=AdvisoryCaseKind(payload.get("kind")),
            issueType=IssueType(payload.get("issueType")),
            severity=AdvisorySeverity(payload.get("severity")),
            state=AdvisoryCaseState.RECEIVED,
            text=payload.get("text"),
        )
        db.add(case)
        db.flush()

        event = AdvisoryEvent(
            advisoryCaseId=case.id,
            actorId=None,
            label="RECEIVED",
            detail=payload.get("detail", "Auto-generated from RabbitMQ worker"),
            stateSnapshot=AdvisoryCaseState.RECEIVED,
        )
        db.add(event)
        
        db.commit()
        logger.info(f"AdvisoryCase created successfully for farm {payload.get('farmId')}.")
        
        # Acknowledge the message so RabbitMQ removes it from queue
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing advisory: {e}")
        logger.error(traceback.format_exc())
        # Requeue once (survives transient DB blips) but drop on the second
        # failure so a genuinely bad message can't loop forever.
        # ponytail: a proper dead-letter exchange is the upgrade for retaining poison messages.
        requeue = not method.redelivered
        if not requeue:
            logger.error("Message already retried once — dropping to avoid an infinite loop.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=requeue)
    finally:
        db.close()


# ── Sync Queue Handler ───────────────────────────────────────

def _upsert_service_center(db, data: dict):
    """Upsert a ServiceCenter record from Agriverse API data."""
    sc_id = data.get("id")
    if not sc_id:
        return
    existing = db.query(ServiceCenter).filter(ServiceCenter.id == sc_id).first()
    if existing:
        existing.name = data.get("name", existing.name)
        existing.region = data.get("region", existing.region)
        existing.phone = data.get("phone", existing.phone)
        if data.get("districtId"):
            existing.districtId = data["districtId"]
    else:
        sc = ServiceCenter(
            id=sc_id,
            name=data.get("name", ""),
            region=data.get("region"),
            phone=data.get("phone"),
            districtId=data.get("districtId"),
        )
        db.add(sc)


def _upsert_user(db, data: dict):
    """Upsert a User record from Agriverse API data."""
    user_id = data.get("id")
    if not user_id:
        return
    existing = db.query(User).filter(User.id == user_id).first()
    if existing:
        existing.firstName = data.get("firstName", existing.firstName)
        existing.lastName = data.get("lastName", existing.lastName)
        existing.email = data.get("email", existing.email)
        existing.isActive = data.get("isActive", existing.isActive)
        existing.availabilityStatus = data.get("availabilityStatus", existing.availabilityStatus)
        if data.get("serviceCenterId"):
            existing.serviceCenterId = data["serviceCenterId"]
    else:
        user = User(
            id=user_id,
            email=data.get("email", ""),
            username=data.get("username", data.get("email", "")),
            password="",  # We don't sync passwords — users auth against Agriverse
            firstName=data.get("firstName", ""),
            lastName=data.get("lastName", ""),
            role=data.get("role", "FIELD_AGENT"),
            isActive=data.get("isActive", True),
            serviceCenterId=data.get("serviceCenterId"),
            availabilityStatus=data.get("availabilityStatus"),
        )
        db.add(user)


def _upsert_farm(db, data: dict):
    """Upsert a Farm record from Agriverse API data."""
    farm_id = data.get("id")
    if not farm_id:
        return
    existing = db.query(Farm).filter(Farm.id == farm_id).first()
    if existing:
        existing.farmer = data.get("farmer", existing.farmer)
        existing.phone = data.get("phone", existing.phone)
        existing.village = data.get("village", existing.village)
        existing.location = data.get("location", existing.location)
        existing.acres = data.get("acres", existing.acres)
        existing.lon = data.get("lon", existing.lon)
        existing.lat = data.get("lat", existing.lat)
        if data.get("serviceCenterId"):
            existing.serviceCenterId = data["serviceCenterId"]
    else:
        farm = Farm(
            id=farm_id,
            farmer=data.get("farmer"),
            phone=data.get("phone"),
            village=data.get("village"),
            location=data.get("location"),
            acres=data.get("acres"),
            lon=data.get("lon"),
            lat=data.get("lat"),
            serviceCenterId=data.get("serviceCenterId"),
        )
        db.add(farm)


def _upsert_field_crop(db, data: dict):
    """Upsert a FieldCrop record from Agriverse API data."""
    fc_id = data.get("id")
    if not fc_id:
        return
    existing = db.query(FieldCrop).filter(FieldCrop.id == fc_id).first()
    if existing:
        existing.crop = data.get("crop", existing.crop)
        existing.variety = data.get("variety", existing.variety)
        if data.get("plantingDate"):
            existing.sowDate = datetime.fromisoformat(data["plantingDate"].replace("Z", "+00:00"))
    else:
        fc = FieldCrop(
            id=fc_id,
            farmId=data.get("farmId"),
            crop=data.get("crop"),
            variety=data.get("variety"),
            sowDate=datetime.fromisoformat(data["plantingDate"].replace("Z", "+00:00")) if data.get("plantingDate") else None,
        )
        db.add(fc)


def _upsert_service(db, data: dict):
    """Upsert a Service catalogue record."""
    svc_id = data.get("id")
    if not svc_id:
        return
    existing = db.query(Service).filter(Service.id == svc_id).first()
    if existing:
        existing.name = data.get("name", existing.name)
        existing.description = data.get("description", existing.description)
        existing.rate = data.get("rate", existing.rate)
        existing.isActive = data.get("isActive", existing.isActive)
    else:
        svc = Service(
            id=svc_id,
            name=data.get("name", ""),
            description=data.get("description"),
            rate=data.get("rate"),
            isActive=data.get("isActive", True),
        )
        db.add(svc)


def _upsert_product(db, data: dict):
    """Upsert a Product catalogue record."""
    prod_id = data.get("id")
    if not prod_id:
        return
    existing = db.query(Product).filter(Product.id == prod_id).first()
    if existing:
        existing.name = data.get("name", existing.name)
        existing.description = data.get("description", existing.description)
        existing.rate = data.get("rate", existing.rate)
        existing.isActive = data.get("isActive", existing.isActive)
    else:
        prod = Product(
            id=prod_id,
            name=data.get("name", ""),
            description=data.get("description"),
            rate=data.get("rate"),
            isActive=data.get("isActive", True),
        )
        db.add(prod)


def _upsert_farm_advisory(db, data: dict):
    """Upsert a FarmAdvisory (Agrobot raw output) record."""
    # FarmAdvisory uses requestId as identifier from the API
    request_id = data.get("requestId")
    farm_id = data.get("farmId")
    if not farm_id:
        return

    # Check if already exists by looking for matching text + farm
    existing = db.query(FarmAdvisory).filter(
        FarmAdvisory.farmId == farm_id,
        FarmAdvisory.advisoryText == data.get("advisoryText"),
    ).first()

    if not existing:
        fa = FarmAdvisory(
            farmId=farm_id,
            fieldCropId=data.get("fieldCropId"),
            advisoryText=data.get("advisoryText"),
            status=data.get("status", "COMPLETE"),
        )
        db.add(fa)


# Dispatch table: entity name → upsert function
_UPSERT_DISPATCH = {
    "service_center": _upsert_service_center,
    "user": _upsert_user,
    "farm": _upsert_farm,
    "field_crop": _upsert_field_crop,
    "service": _upsert_service,
    "product": _upsert_product,
    "farm_advisory": _upsert_farm_advisory,
}


def process_sync_update(ch, method, properties, body):
    """Process a batch of sync updates from the delta sync service."""
    payload = json.loads(body)
    batch = payload.get("batch", [])
    count = payload.get("count", 0)

    logger.info(f"Received sync update batch with {count} record(s).")

    db = SessionLocal()
    try:
        processed = 0
        for record in batch:
            entity = record.get("entity")
            data = record.get("data")

            if not entity or not data:
                logger.warning(f"Skipping sync record with missing entity/data: {record}")
                continue

            upsert_fn = _UPSERT_DISPATCH.get(entity)
            if not upsert_fn:
                logger.warning(f"Unknown sync entity type: {entity}")
                continue

            try:
                upsert_fn(db, data)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to upsert {entity} (id={data.get('id')}): {e}")
                # Continue with next record — don't fail the whole batch

        db.commit()
        logger.info(f"Sync batch committed: {processed}/{count} records upserted.")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing sync batch: {e}")
        logger.error(traceback.format_exc())
        requeue = not method.redelivered
        if not requeue:
            logger.error("Sync batch already retried once — dropping.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=requeue)
    finally:
        db.close()


# ── Main ─────────────────────────────────────────────────────

def main():
    logger.info("Worker starting... waiting for RabbitMQ connection.")
    # Simple retry mechanism for connection
    while True:
        try:
            connection = get_connection()
            break
        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ not ready. Retrying in 5 seconds...")
            time.sleep(5)

    channel = connection.channel()

    # Declare both queues
    channel.queue_declare(queue=ADVISORY_QUEUE, durable=True)
    channel.queue_declare(queue=SYNC_QUEUE, durable=True)

    channel.basic_qos(prefetch_count=1)

    # Register consumers for both queues
    channel.basic_consume(queue=ADVISORY_QUEUE, on_message_callback=process_advisory)
    channel.basic_consume(queue=SYNC_QUEUE, on_message_callback=process_sync_update)

    logger.info(f"Worker connected. Listening to '{ADVISORY_QUEUE}' and '{SYNC_QUEUE}'...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()

if __name__ == "__main__":
    main()

