"""
RabbitMQ Producer for publishing advisories asynchronously.
"""

import json
import pika
import logging
from config import get_settings

logger = logging.getLogger("fams.rabbitmq")
settings = get_settings()

QUEUE_NAME = "advisories_queue"

def get_connection():
    parameters = pika.URLParameters(settings.RABBITMQ_URL)
    return pika.BlockingConnection(parameters)

def publish_advisory(payload: dict):
    """Publish an advisory dictionary to RabbitMQ."""
    try:
        connection = get_connection()
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        connection.close()
    except Exception as e:
        logger.error(f"Failed to publish advisory to RabbitMQ: {e}")
        # Depending on criticality, you might raise it or fall back to sync db writes.
        raise
