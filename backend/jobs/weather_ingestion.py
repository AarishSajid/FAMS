"""
Background job to pre-fetch weather data hourly.
In a real app, this would cache data in Redis per district/coordinate.

"""

import json
import logging
from database import SessionLocal
from models.service_center import ServiceCenter
from models.farm import Farm
from services.weather_service import fetch_current_weather
from redis_client import redis_client

logger = logging.getLogger("fams.jobs.weather")


async def run_weather_ingestion():
    """APScheduler wrapper for hourly weather ingestion."""
    logger.info("Running scheduled weather ingestion job...")
    
    db = SessionLocal()
    try:
        centers = db.query(ServiceCenter).all()
        for center in centers:
            # Grab the first farm in the center to use as the GPS anchor
            farm = db.query(Farm).filter(Farm.serviceCenterId == center.id, Farm.lat.isnot(None), Farm.lon.isnot(None)).first()
            if not farm:
                continue
                
            lat, lon = farm.lat, farm.lon
            
            try:
                data = await fetch_current_weather(lat, lon)
                if data:
                    logger.info(f"Fetched weather for {center.name} ({lat}, {lon}): {data['temp']}°C, {data['description']}")
                    # Save this to Redis using the center.id
                    redis_client.set(f"weather:center:{center.id}", json.dumps(data), ex=3600)
            except Exception as e:
                logger.error(f"Error fetching weather for {center.name}: {e}")
    except Exception as e:
        logger.error(f"Weather ingestion failed: {e}")
    finally:
        db.close()
