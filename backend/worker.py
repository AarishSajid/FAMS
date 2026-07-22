"""
RabbitMQ Consumer background worker.
Listens to 'advisories_queue', simulates processing work, and writes AdvisoryCases to the DB.
"""

import json
import time
import pika
import logging
import traceback
from config import get_settings
from database import SessionLocal
from models.advisory import AdvisoryCase, AdvisoryEvent
from enums import AdvisoryCaseState, AdvisoryCaseKind, IssueType, AdvisorySeverity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fams.worker")

settings = get_settings()
QUEUE_NAME = "advisories_queue"

def get_connection():
    parameters = pika.URLParameters(settings.RABBITMQ_URL)
    return pika.BlockingConnection(parameters)

def process_message(ch, method, properties, body):
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
        # Negative ack so it requeues or drops based on dead letter config
        # For simplicity, requeue=False to avoid infinite loops if it's a schema error
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    finally:
        db.close()

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
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_message)

    logger.info(f"Worker connected. Listening to '{QUEUE_NAME}'...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()

if __name__ == "__main__":
    main()
